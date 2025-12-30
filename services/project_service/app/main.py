import os
import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from .models import Book
from .routes_books import router as books_router

# =========================
# DATABASE INIT
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# APP INIT
# =========================
app = FastAPI(title="Project Service - Perpustakaan")

app.include_router(books_router)

@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# UPLOAD CONFIG
# =========================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# =========================
# UPLOAD PDF ENDPOINT
# =========================
@app.post("/books/{id_buku}/pdf")
async def upload_book_pdf(
    id_buku: int,
    file: UploadFile = File(...)
):
    # validasi ekstensi
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus PDF (.pdf)")

    db = SessionLocal()
    try:
        # cek buku
        book = db.query(Book).filter(Book.id_buku == id_buku).first()
        if not book:
            raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

        # nama file unik
        filename = f"{id_buku}_{uuid.uuid4().hex}.pdf"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # simpan file
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # simpan URL ke DB
        book.pdf_url = f"/uploads/{filename}"
        db.commit()

        return {
            "message": "PDF berhasil diupload",
            "pdf_url": book.pdf_url
        }

    finally:
        db.close()
