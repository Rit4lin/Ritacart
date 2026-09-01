from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    receipts: Mapped[list[Receipt]] = relationship(back_populates="store")
    aliases: Mapped[list[ProductAlias]] = relationship(back_populates="store")


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("source_message_id", "source_attachment_index", name="uq_receipt_message_attachment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_attachment_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_pdf_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    parser_warnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    store: Mapped[Store] = relationship(back_populates="receipts")
    items: Mapped[list[ReceiptItem]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    aliases: Mapped[list[ProductAlias]] = relationship(back_populates="product")
    receipt_items: Mapped[list[ReceiptItem]] = relationship(back_populates="product")


class ProductAlias(Base):
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("store_id", "raw_name", name="uq_product_alias_store_raw_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    store: Mapped[Store] = relationship(back_populates="aliases")
    product: Mapped[Product] = relationship(back_populates="aliases")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    price_per_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    total_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="items")
    product: Mapped[Optional[Product]] = relationship(back_populates="receipt_items")
