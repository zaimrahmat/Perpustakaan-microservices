import os
import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File

BASE_DIR = Path(__file__).resolve().parent  # folder app/
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

AUTH = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
PROJ = os.getenv("PROJECT_SERVICE_URL", "http://project_service:8000")

app = FastAPI(title="Gateway Service")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(templates_dir))

# =========================
# UI ROUTES
# =========================
@app.get("/", response_class=HTMLResponse)
def ui_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def ui_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def ui_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# =========================
# HEALTH + BUILD
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/build")
def build_info():
    return {"GATEWAY_BUILD_MARKER": "GW_FINAL_NO_INTERNAL_REDIRECT"}

# =========================
# HELPERS
# =========================
def _norm(path: str) -> str:
    # Hilangkan leading/trailing slash agar tidak memicu redirect_slashes di backend
    return (path or "").strip("/")

def _forward_headers(request: Request) -> dict:
    # Forward semua header kecuali Host
    h = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    # Pastikan backend menganggap request aslinya HTTPS (karena dari browser ke gateway memang HTTPS)
    h["x-forwarded-proto"] = "https"
    return h

def _sanitize_response_headers(h: dict) -> dict:
    # Jangan kirim header encoding/transfer yang bisa bikin client bingung
    h.pop("content-encoding", None)
    h.pop("transfer-encoding", None)

    # Jika backend mengirim redirect ke URL internal ContainerApps, buang Location-nya.
    # (Login API seharusnya balas JSON, bukan redirect.)
    h.pop("location", None)
    h.pop("Location", None)

    return h

# =========================
# UPLOAD FILE (PDF)
# =========================
@app.post("/api/books/{id_buku}/pdf")
async def upload_book_pdf(id_buku: int, file: UploadFile = File(...), request: Request = None):
    # ambil token dari request (biar auth tetap jalan)
    auth = request.headers.get("authorization")

    # forward multipart ke project_service
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {
            "file": (file.filename, await file.read(), file.content_type or "application/pdf")
        }
        headers = {}
        if auth:
            headers["Authorization"] = auth

        r = await client.post(f"{PROJ}/books/{id_buku}/pdf", files=files, headers=headers)

    return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type"))

# =========================
# PROXY ROUTES (AUTH & API)
# =========================
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE","HEAD"])
async def proxy_auth(path: str, request: Request):
    p = _norm(path)
    url = f"{AUTH}/{p}" if p else AUTH

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False, verify=False) as client:
        resp = await client.request(
            request.method,
            url,
            headers=_forward_headers(request),
            params=dict(request.query_params),
            content=await request.body(),
        )

    headers = _sanitize_response_headers(dict(resp.headers))
    return Response(content=resp.content, status_code=resp.status_code, headers=headers)

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE","HEAD"])
async def proxy_project(path: str, request: Request):
    p = _norm(path)
    url = f"{PROJ}/{p}" if p else PROJ

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        resp = await client.request(
            request.method,
            url,
            headers=_forward_headers(request),
            params=dict(request.query_params),
            content=await request.body(),
        )

    headers = _sanitize_response_headers(dict(resp.headers))
    return Response(content=resp.content, status_code=resp.status_code, headers=headers)

# ========= STATIC UPLOADS =========
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")  # PAKAI PATH ABSOLUT
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
