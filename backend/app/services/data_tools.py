from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Product, ProductAlias, Receipt, ReceiptItem, Store


def decode_parser_warnings(value: str | None) -> list[str]:
    """Decode persisted parser warnings without letting malformed legacy data break the UI."""
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return ["Avisos del parser almacenados con un formato no válido"]
    if not isinstance(decoded, list):
        return ["Avisos del parser almacenados con un formato no válido"]
    return [str(item) for item in decoded]


def search(session: Session, query: str, limit: int = 10) -> dict[str, list[dict[str, object]]]:
    term = query.strip()
    if not term:
        return {"products": [], "receipts": []}
    try:
        date_term = datetime.strptime(term, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        date_term = term
    pattern = f"%{term}%"
    date_pattern = f"%{date_term}%"
    products = session.scalars(
        select(Product).outerjoin(ProductAlias).where(or_(Product.name.ilike(pattern), ProductAlias.raw_name.ilike(pattern))).distinct().limit(limit)
    ).all()
    receipts = session.scalars(
        select(Receipt).join(Receipt.store).outerjoin(Receipt.items).outerjoin(ReceiptItem.product)
        .where(or_(Store.name.ilike(pattern), Product.name.ilike(pattern), ReceiptItem.raw_name.ilike(pattern), func.strftime("%Y-%m-%d", Receipt.purchased_at).like(date_pattern)))
        .options(selectinload(Receipt.store), selectinload(Receipt.items)).distinct().order_by(Receipt.purchased_at.desc()).limit(limit)
    ).all()
    return {"products": [{"id": product.id, "name": product.name} for product in products], "receipts": [{"id": receipt.id, "store": receipt.store.name, "purchased_at": receipt.purchased_at.isoformat(), "total": str(receipt.total), "item_count": len(receipt.items)} for receipt in receipts]}


def data_health(session: Session) -> dict[str, int]:
    receipts = session.scalars(select(Receipt).options(selectinload(Receipt.items))).all()
    decoded_warnings = {receipt.id: decode_parser_warnings(receipt.parser_warnings) for receipt in receipts}
    warnings = sum(len(values) for values in decoded_warnings.values())
    review = [receipt for receipt in receipts if not receipt.items or decoded_warnings[receipt.id]]
    duplicate_groups = session.execute(select(Receipt.store_id, Receipt.purchased_at, Receipt.total, func.count(Receipt.id)).group_by(Receipt.store_id, Receipt.purchased_at, Receipt.total).having(func.count(Receipt.id) > 1)).all()
    return {"total_receipts": len(receipts), "total_receipt_items": sum(len(receipt.items) for receipt in receipts), "total_products": session.scalar(select(func.count(Product.id))) or 0, "uncategorized_products": session.scalar(select(func.count(Product.id)).where(Product.category_id.is_(None))) or 0, "receipts_needing_review": len(review), "receipts_without_items": sum(not receipt.items for receipt in receipts), "possible_duplicate_receipts": len(duplicate_groups), "parser_warning_count": warnings}


def decimal_or_none(value: str | None, field: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} debe ser un decimal válido") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} debe ser un valor no negativo")
    return result


def csv_export(session: Session, kind: str) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    if kind == "receipts":
        writer.writerow(["receipt_id", "purchased_at", "store", "total", "source_filename"])
        for receipt in session.scalars(select(Receipt).options(selectinload(Receipt.store)).order_by(Receipt.purchased_at)):
            writer.writerow([receipt.id, receipt.purchased_at.isoformat(), receipt.store.name, receipt.total, receipt.source_filename])
    elif kind == "items":
        writer.writerow(["receipt_id", "purchased_at", "store", "product_id", "product_name", "category", "raw_description", "quantity", "unit", "unit_price", "price_per_kg", "total_price"])
        items = session.scalars(select(ReceiptItem).options(selectinload(ReceiptItem.receipt).selectinload(Receipt.store), selectinload(ReceiptItem.product).selectinload(Product.category))).all()
        for item in items:
            writer.writerow([item.receipt_id, item.receipt.purchased_at.isoformat(), item.receipt.store.name, item.product_id, item.product.name if item.product else "", item.product.category.name if item.product and item.product.category else "", item.raw_name, item.quantity or "", item.unit or "", item.unit_price or "", item.price_per_kg or "", item.total_price or ""])
    elif kind == "products":
        writer.writerow(["product_id", "name", "category"])
        for product in session.scalars(select(Product).options(selectinload(Product.category)).order_by(Product.name)):
            writer.writerow([product.id, product.name, product.category.name if product.category else ""])
    else:
        raise ValueError("Exportación no encontrada")
    return "\ufeff" + output.getvalue()
