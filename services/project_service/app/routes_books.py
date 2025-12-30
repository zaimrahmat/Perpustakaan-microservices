import os, uuid, shutil
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from . import schemas, crud_books
from .security import require_admin, get_current_user
from .models import Book

router = APIRouter(prefix="/books", tags=["Books"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# ADMIN ONLY (CREATE)
# =========================
@router.post(
    "",
    response_model=schemas.BookOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)]
)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)):
    return crud_books.create_book(db, payload)

# =========================
# USER/ADMIN (READ ALL)
# =========================
@router.get(
    "",
    response_model=list[schemas.BookOut],
    dependencies=[Depends(get_current_user)]
)
def list_books(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return crud_books.list_books(db, skip, limit)

# =========================
# USER/ADMIN (READ ONE)
# =========================
@router.get(
    "/{id_buku}",
    response_model=schemas.BookOut,
    dependencies=[Depends(get_current_user)]
)
def get_book(id_buku: int, db: Session = Depends(get_db)):
    return crud_books.get_book(db, id_buku)

# =========================
# ADMIN ONLY (UPDATE)
# =========================
@router.put(
    "/{id_buku}",
    response_model=schemas.BookOut,
    dependencies=[Depends(require_admin)]
)
def update_book(id_buku: int, payload: schemas.BookUpdate, db: Session = Depends(get_db)):
    return crud_books.update_book(db, id_buku, payload)

# =========================
# ADMIN ONLY (DELETE)
# =========================
@router.delete(
    "/{id_buku}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)]
)
def delete_book(id_buku: int, db: Session = Depends(get_db)):
    crud_books.delete_book(db, id_buku)
    return None

# =========================
# ADMIN ONLY (UPLOAD PDF)
# =========================
@router.post(
    "/{id_buku}/pdf",
    dependencies=[Depends(require_admin)]
)
async def upload_book_pdf(
    id_buku: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File harus PDF")

    book = db.query(Book).filter(Book.id_buku == id_buku).first()
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

    filename = f"{id_buku}_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 🔥 cara simpan paling aman
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File kosong / gagal terbaca")

    with open(filepath, "wb") as f:
        f.write(content)

    # cek ukuran
    size = os.path.getsize(filepath)
    if size <= 0:
        raise HTTPException(status_code=500, detail="File tersimpan tapi ukuran 0 byte")

    book.pdf_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(book)

    return {
        "message": "PDF berhasil diupload",
        "pdf_url": book.pdf_url,
        "bytes": size
    }
