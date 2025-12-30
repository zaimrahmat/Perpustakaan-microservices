from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Category(Base):
    __tablename__ = "categories"

    id_kategori = Column(Integer, primary_key=True, autoincrement=True)
    nama = Column(String(100), unique=True, nullable=False)

    books = relationship("Book", back_populates="category")

class Book(Base):
    __tablename__ = "books"

    id_buku = Column(Integer, primary_key=True, autoincrement=False, index=True)

    judul = Column(String(200), nullable=False)
    penulis = Column(String(150), nullable=False)
    tahun = Column(Integer, nullable=True)

    tersedia = Column(Boolean, default=True, nullable=False)

    # PENTING
    pdf_url = Column(String, nullable=True)

    id_kategori = Column(Integer, ForeignKey("categories.id_kategori"), nullable=True)
    category = relationship("Category", back_populates="books")
