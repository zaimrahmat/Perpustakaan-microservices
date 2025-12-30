import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt

from .database import Base, engine, get_db
from .models import User
from .schemas import RegisterIn, LoginIn, TokenOut

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "120"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(redirect_slashes=False, title="Auth Service")

Base.metadata.create_all(bind=engine)

# =========================
# UTIL
# =========================
def create_access_token(sub: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {
        "sub": sub,
        "r": "a" if role == "admin" else "u",
        "exp": exp
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

# =========================
# SEED ADMIN
# =========================
@app.on_event("startup")
def seed_admin():
    db = Session(bind=engine)
    try:
        admin = db.execute(
            select(User).where(User.username == ADMIN_USERNAME)
        ).scalar_one_or_none()

        if not admin:
            admin = User(
                username=ADMIN_USERNAME,
                password_hash=pwd_context.hash(ADMIN_PASSWORD),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("Admin account created")
    finally:
        db.close()

# =========================
# ROUTES
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Username sudah terpakai.")

    user = User(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        role="user"   #  user only
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "username": user.username, "role": "user"}

@app.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username/password salah.")

    token = create_access_token(user.username, user.role)
    return {"access_token": token, "token_type": "bearer"}
