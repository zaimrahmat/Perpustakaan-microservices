from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from . import models, schemas

def create_book(db: Session, payload: schemas.BookCreate) -> models.Book:
    # Pastikan id_buku tidak bentrok
    exists = db.execute(select(models.Book).where(models.Book.id_buku == payload.id_buku)).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"id_buku {payload.id_buku} sudah digunakan."
        )

    book = models.Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

def get_book(db: Session, id_buku: int) -> models.Book:
    book = db.execute(select(models.Book).where(models.Book.id_buku == id_buku)).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan.")
    return book

def list_books(db: Session, skip: int = 0, limit: int = 20):
    return db.execute(select(models.Book).offset(skip).limit(limit)).scalars().all()

def update_book(db: Session, id_buku: int, payload: schemas.BookUpdate) -> models.Book:
    book = get_book(db, id_buku)
    data = payload.model_dump(exclude_unset=True)

    for k, v in data.items():
        setattr(book, k, v)

    db.commit()
    db.refresh(book)
    return book

def delete_book(db: Session, id_buku: int) -> None:
    book = get_book(db, id_buku)
    db.delete(book)
    db.commit()