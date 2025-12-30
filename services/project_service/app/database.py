import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# =========================
# DATABASE CONFIG (POSTGRES ONLY)
# =========================
DATABASE_URL = os.getenv("PROJECT_DB_URL")

if not DATABASE_URL:
    raise RuntimeError("PROJECT_DB_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
