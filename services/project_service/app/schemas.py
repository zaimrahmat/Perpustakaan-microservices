from pydantic import BaseModel, Field
from typing import Optional

class BookBase(BaseModel):
    judul: str = Field(min_length=1, max_length=200)
    penulis: str = Field(min_length=1, max_length=150)
    tahun: Optional[int] = Field(default=None, ge=0, le=2100)
    tersedia: bool = True
    id_kategori: Optional[int] = None

class BookCreate(BookBase):
    # ID diinput admin
    id_buku: int = Field(ge=1)

class BookUpdate(BaseModel):
    judul: Optional[str] = Field(default=None, min_length=1, max_length=200)
    penulis: Optional[str] = Field(default=None, min_length=1, max_length=150)
    tahun: Optional[int] = Field(default=None, ge=0, le=2100)
    tersedia: Optional[bool] = None
    id_kategori: Optional[int] = None

class BookOut(BookBase):
    id_buku: int
    pdf_url: Optional[str] = None

    class Config:
        from_attributes = True