from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from ..models import Product, ProductAlias, Receipt, ReceiptItem


def _decimal(value: Decimal | None) -> str:
    return str(value or Decimal("0"))


def _product_query():
    return select(Product).options(
        selectinload(Product.aliases),
        selectinload(Product.receipt_items).selectinload(ReceiptItem.receipt),
    )


def _summary(product: Product) -> dict[str, object]:
    items = product.receipt_items
    receipt_ids = {item.receipt_id for item in items}
    quantities = sum((item.quantity or Decimal("0")) for item in items)
    latest = max((item.receipt.purchased_at for item in items), default=None)
    return {
        "id": product.id,
        "name": product.name,
        "purchase_count": len(receipt_ids),
        "total_quantity": _decimal(quantities),
        "last_purchased_at": latest.isoformat() if latest else None,
    }


def list_products(session: Session) -> list[dict[str, object]]:
    products = session.scalars(_product_query()).all()
    return sorted(
        (_summary(product) for product in products),
        key=lambda product: (-int(product["purchase_count"]), str(product["name"]).casefold()),
    )


def top_products(session: Session, limit: int = 5) -> list[dict[str, object]]:
    return list_products(session)[:limit]


def product_analytics(session: Session, product_id: int) -> dict[str, object] | None:
    product = session.scalar(_product_query().where(Product.id == product_id))
    if product is None:
        return None

    monthly: dict[str, dict[str, object]] = {}
    seasonal: dict[int, dict[str, object]] = {}
    daily_prices: dict[tuple[str, str], Decimal] = {}
    for item in product.receipt_items:
        purchased_at = item.receipt.purchased_at
        month_key = purchased_at.strftime("%Y-%m")
        month = monthly.setdefault(month_key, {"receipt_ids": set(), "quantity": Decimal("0")})
        month["receipt_ids"].add(item.receipt_id)  # type: ignore[union-attr]
        month["quantity"] += item.quantity or Decimal("0")  # type: ignore[operator]

        season = seasonal.setdefault(purchased_at.month, {"receipt_ids": set()})
        season["receipt_ids"].add(item.receipt_id)  # type: ignore[union-attr]

        price, price_unit = _observed_price(item)
        if price is not None:
            key = (purchased_at.date().isoformat(), price_unit)
            daily_prices[key] = max(daily_prices.get(key, price), price)

    return {
        **_summary(product),
        "aliases": sorted(alias.raw_name for alias in product.aliases),
        "monthly_purchases": [
            {
                "month": month,
                "purchase_count": len(values["receipt_ids"]),
                "total_quantity": _decimal(values["quantity"]),
            }
            for month, values in sorted(monthly.items())
        ],
        "seasonal_purchases": [
            {"month": month, "purchase_count": len(values["receipt_ids"])}
            for month, values in sorted(seasonal.items())
        ],
        "price_history": [
            {"date": date, "price": _decimal(price), "price_unit": price_unit}
            for (date, price_unit), price in sorted(daily_prices.items())
        ],
    }


def merge_products(session: Session, source_product_id: int, target_product_id: int) -> dict[str, object] | None:
    if source_product_id == target_product_id:
        raise ValueError("El producto de origen y destino deben ser distintos")
    source = session.get(Product, source_product_id)
    target = session.get(Product, target_product_id)
    if source is None or target is None:
        return None
    source_name = source.name
    target_name = target.name

    session.execute(
        update(ProductAlias)
        .where(ProductAlias.product_id == source.id)
        .values(product_id=target.id)
    )
    session.execute(
        update(ReceiptItem)
        .where(ReceiptItem.product_id == source.id)
        .values(product_id=target.id)
    )
    session.execute(delete(Product).where(Product.id == source.id))
    session.commit()
    return {"source_name": source_name, "target_name": target_name, "product_id": target.id}


def rename_product(session: Session, product_id: int, name: str) -> dict[str, object] | None:
    canonical_name = " ".join(name.split())
    if not canonical_name:
        raise ValueError("El nombre del producto no puede estar vacío")
    if len(canonical_name) > 255:
        raise ValueError("El nombre del producto no puede superar 255 caracteres")
    product = session.get(Product, product_id)
    if product is None:
        return None
    existing = session.scalar(
        select(Product).where(Product.name == canonical_name, Product.id != product.id)
    )
    if existing is not None:
        raise ValueError("Ya existe otro producto con ese nombre")
    product.name = canonical_name
    session.commit()
    return {"product_id": product.id, "name": product.name}


def _observed_price(item: ReceiptItem) -> tuple[Decimal | None, str]:
    if item.price_per_kg is not None:
        return item.price_per_kg, "€/kg"
    if item.unit_price is not None:
        return item.unit_price, "€/ud"
    if item.total_price is not None and item.quantity not in (None, Decimal("0")):
        return item.total_price / item.quantity, "€/ud"
    return None, "€/ud"
