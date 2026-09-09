from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from ..models import Category, Product, ProductAlias, Receipt, ReceiptItem


def _decimal(value: Decimal | None) -> str:
    return str(value or Decimal("0"))


def _money(value: Decimal | None) -> str | None:
    return str(value.quantize(Decimal("0.01"))) if value is not None else None


def _product_query():
    return select(Product).options(
        selectinload(Product.aliases),
        selectinload(Product.category),
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
        "category": _category_payload(product.category),
    }


def _category_payload(category: Category | None) -> dict[str, object] | None:
    if category is None:
        return None
    return {"id": category.id, "name": category.name, "slug": category.slug}


def _daily_prices(product: Product) -> dict[tuple[str, str], Decimal]:
    prices: dict[tuple[str, str], Decimal] = {}
    for item in product.receipt_items:
        price, price_unit = _observed_price(item)
        if price is not None:
            key = (item.receipt.purchased_at.date().isoformat(), price_unit)
            prices[key] = max(prices.get(key, price), price)
    return prices


def _price_summary(daily_prices: dict[tuple[str, str], Decimal]) -> list[dict[str, str | None]]:
    by_unit: dict[str, list[tuple[str, Decimal]]] = {}
    for (date, unit), price in daily_prices.items():
        by_unit.setdefault(unit, []).append((date, price))
    summaries: list[dict[str, str | None]] = []
    for unit, observations in sorted(by_unit.items()):
        observations.sort()
        prices = [price for _, price in observations]
        current = prices[-1]
        previous = prices[-2] if len(prices) > 1 else None
        change = current - previous if previous is not None else None
        percent = (change / previous * Decimal("100")) if change is not None and previous else None
        summaries.append({
            "price_unit": unit,
            "current_price": _money(current),
            "previous_price": _money(previous),
            "change_absolute": _money(change),
            "change_percent": str(percent.quantize(Decimal("0.1"))) if percent is not None else None,
            "min_price": _money(min(prices)),
            "max_price": _money(max(prices)),
            "average_price": _money(sum(prices, Decimal("0")) / len(prices)),
        })
    return summaries


def list_products(session: Session) -> list[dict[str, object]]:
    products = session.scalars(_product_query()).all()
    return sorted(
        (_summary(product) for product in products),
        key=lambda product: (-int(product["purchase_count"]), str(product["name"]).casefold()),
    )


def top_products(session: Session, limit: int = 5) -> list[dict[str, object]]:
    # Keep the compact historical ranking payload stable; category is exposed by /products.
    return [
        {key: value for key, value in product.items() if key != "category"}
        for product in list_products(session)[:limit]
    ]


def product_analytics(session: Session, product_id: int) -> dict[str, object] | None:
    product = session.scalar(_product_query().where(Product.id == product_id))
    if product is None:
        return None

    monthly: dict[str, dict[str, object]] = {}
    seasonal: dict[int, dict[str, object]] = {}
    monthly_spend: dict[str, Decimal] = {}
    receipt_dates: dict[int, datetime] = {}
    total_spend = Decimal("0")
    for item in product.receipt_items:
        purchased_at = item.receipt.purchased_at
        month_key = purchased_at.strftime("%Y-%m")
        month = monthly.setdefault(month_key, {"receipt_ids": set(), "quantity": Decimal("0")})
        month["receipt_ids"].add(item.receipt_id)  # type: ignore[union-attr]
        month["quantity"] += item.quantity or Decimal("0")  # type: ignore[operator]

        season = seasonal.setdefault(purchased_at.month, {"receipt_ids": set()})
        season["receipt_ids"].add(item.receipt_id)  # type: ignore[union-attr]
        receipt_dates[item.receipt_id] = purchased_at
        if item.total_price is not None:
            total_spend += item.total_price
            monthly_spend[month_key] = monthly_spend.get(month_key, Decimal("0")) + item.total_price

    daily_prices = _daily_prices(product)
    purchase_dates = sorted({value.date() for value in receipt_dates.values()})
    intervals = [(later - earlier).days for earlier, later in zip(purchase_dates, purchase_dates[1:])]
    first_purchase = min(receipt_dates.values(), default=None)
    last_purchase = max(receipt_dates.values(), default=None)

    return {
        **_summary(product),
        "first_purchased_at": first_purchase.isoformat() if first_purchase else None,
        "total_spend": _money(total_spend),
        "average_days_between_purchases": (
            str((Decimal(sum(intervals)) / len(intervals)).quantize(Decimal("0.1"))) if intervals else None
        ),
        "price_summary": _price_summary(daily_prices),
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
        "monthly_spend": [
            {"month": month, "total_spend": _money(total)}
            for month, total in sorted(monthly_spend.items())
        ],
        "price_history": [
            {"date": date, "price": _decimal(price), "price_unit": price_unit}
            for (date, price_unit), price in sorted(daily_prices.items())
        ],
    }


def product_insights(session: Session, limit: int = 10) -> dict[str, list[dict[str, object]]]:
    """Return historical product rankings without per-product database queries."""
    products = session.scalars(_product_query()).all()
    spend_ranking: list[dict[str, object]] = []
    frequency_ranking: list[dict[str, object]] = []
    price_changes: list[dict[str, object]] = []
    for product in products:
        summary = _summary(product)
        total_spend = sum(
            (item.total_price for item in product.receipt_items if item.total_price is not None),
            Decimal("0"),
        )
        base = {
            "id": product.id,
            "name": product.name,
            "purchase_count": summary["purchase_count"],
            "last_purchased_at": summary["last_purchased_at"],
        }
        if total_spend:
            spend_ranking.append({**base, "total_spend": _money(total_spend)})
        frequency_ranking.append(base)
        for price in _price_summary(_daily_prices(product)):
            if price["change_absolute"] is not None:
                price_changes.append({**base, **price})

    name_key = lambda entry: str(entry["name"]).casefold()
    frequency_ranking.sort(key=name_key)
    frequency_ranking.sort(key=lambda entry: str(entry["last_purchased_at"] or ""), reverse=True)
    frequency_ranking.sort(key=lambda entry: int(entry["purchase_count"]), reverse=True)
    return {
        "most_expensive_by_spend": sorted(spend_ranking, key=lambda entry: (-Decimal(str(entry["total_spend"])), name_key(entry)))[:limit],
        "most_frequently_purchased": frequency_ranking[:limit],
        "biggest_price_increases_percent": sorted((entry for entry in price_changes if Decimal(str(entry["change_percent"] or "0")) > 0), key=lambda entry: Decimal(str(entry["change_percent"])), reverse=True)[:limit],
        "biggest_price_decreases_percent": sorted((entry for entry in price_changes if Decimal(str(entry["change_percent"] or "0")) < 0), key=lambda entry: Decimal(str(entry["change_percent"])))[:limit],
        "biggest_price_increases_absolute": sorted((entry for entry in price_changes if Decimal(str(entry["change_absolute"] or "0")) > 0), key=lambda entry: Decimal(str(entry["change_absolute"])), reverse=True)[:limit],
        "biggest_price_decreases_absolute": sorted((entry for entry in price_changes if Decimal(str(entry["change_absolute"] or "0")) < 0), key=lambda entry: Decimal(str(entry["change_absolute"])))[:limit],
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
    if target.category_id is None and source.category_id is not None:
        target.category_id = source.category_id

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
