from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Category, Product, Receipt, ReceiptItem
from .statistics import StatisticsRange, _add_months, _month_start, _range_start

UNCATEGORIZED = {"category_id": None, "name": "Sin categoría", "slug": "uncategorized"}


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _category_key(category: Category | None) -> int | None:
    return category.id if category else None


def _category_payload(category: Category | None) -> dict[str, object]:
    return {"category_id": category.id, "name": category.name, "slug": category.slug} if category else dict(UNCATEGORIZED)


def _comparison(current: Decimal, previous: Decimal) -> tuple[str, str | None]:
    difference = current - previous
    percentage = difference / previous * Decimal("100") if previous else None
    return _money(difference), str(percentage.quantize(Decimal("0.1"))) if percentage is not None else None


def category_analytics(
    session: Session, selected_range: StatisticsRange, now: datetime
) -> dict[str, object]:
    """Derive category analytics from current product classifications and receipt items."""
    categories = session.scalars(select(Category).order_by(Category.sort_order)).all()
    products = session.scalars(select(Product).options(selectinload(Product.category))).all()
    items = session.scalars(
        select(ReceiptItem).options(
            selectinload(ReceiptItem.receipt),
            selectinload(ReceiptItem.product).selectinload(Product.category),
        )
    ).all()
    start = _range_start(now, selected_range)
    selected_items = [
        item for item in items
        if item.total_price is not None and (start is None or item.receipt.purchased_at >= start)
    ]
    month_start = _month_start(now)
    previous_month_start = _add_months(month_start, -1)

    total_by_category: dict[int | None, Decimal] = defaultdict(lambda: Decimal("0"))
    current_by_category: dict[int | None, Decimal] = defaultdict(lambda: Decimal("0"))
    previous_by_category: dict[int | None, Decimal] = defaultdict(lambda: Decimal("0"))
    receipt_ids: dict[int | None, set[int]] = defaultdict(set)
    product_spend: dict[int | None, dict[int, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    monthly: dict[str, dict[int | None, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for item in items:
        if item.total_price is None:
            continue
        key = _category_key(item.product.category if item.product else None)
        purchased_at = item.receipt.purchased_at
        if month_start <= purchased_at < _add_months(month_start, 1):
            current_by_category[key] += item.total_price
        elif previous_month_start <= purchased_at < month_start:
            previous_by_category[key] += item.total_price
        if start is None or purchased_at >= start:
            total_by_category[key] += item.total_price
            receipt_ids[key].add(item.receipt_id)
            if item.product_id is not None:
                product_spend[key][item.product_id] += item.total_price
            monthly[purchased_at.strftime("%Y-%m")][key] += item.total_price

    product_counts: dict[int | None, int] = defaultdict(int)
    product_lookup = {product.id: product for product in products}
    for product in products:
        product_counts[_category_key(product.category)] += 1
    all_keys = [category.id for category in categories] + [None]
    observed_total = sum(total_by_category.values(), Decimal("0"))
    category_rows: list[dict[str, object]] = []
    for key in all_keys:
        category = next((category for category in categories if category.id == key), None)
        total = total_by_category[key]
        difference, percentage = _comparison(current_by_category[key], previous_by_category[key])
        top_products = [
            {"id": product_id, "name": product_lookup[product_id].name, "total_spend": _money(spend)}
            for product_id, spend in sorted(product_spend[key].items(), key=lambda entry: (-entry[1], product_lookup[entry[0]].name.casefold()))[:5]
        ]
        category_rows.append({
            **_category_payload(category),
            "total_spend": _money(total),
            "percentage": str((total / observed_total * Decimal("100")).quantize(Decimal("0.1"))) if observed_total else "0.0",
            "purchase_count": len(receipt_ids[key]),
            "product_count": product_counts[key],
            "current_month_spend": _money(current_by_category[key]),
            "previous_month_spend": _money(previous_by_category[key]),
            "change_absolute": difference,
            "change_percent": percentage,
            "top_products": top_products,
        })
    category_rows.sort(key=lambda category: (-Decimal(str(category["total_spend"])), str(category["name"])))

    period_start = start or min((item.receipt.purchased_at for item in selected_items), default=None)
    period_end = now if start else max((item.receipt.purchased_at for item in selected_items), default=None)
    monthly_spend: list[dict[str, object]] = []
    if period_start and period_end:
        cursor = _month_start(period_start)
        while cursor <= _month_start(period_end):
            values = monthly[cursor.strftime("%Y-%m")]
            monthly_spend.append({
                "month": cursor.strftime("%Y-%m"),
                "categories": [
                    {"category_id": key, "slug": _category_payload(next((category for category in categories if category.id == key), None))["slug"], "total_spend": _money(values[key])}
                    for key in all_keys
                    if values[key] or product_counts[key]
                ],
            })
            cursor = _add_months(cursor, 1)

    categorized = sum(product_counts[category.id] for category in categories)
    total_products = len(products)
    return {
        "range": selected_range,
        "summary": {
            "total_products": total_products,
            "categorized_products": categorized,
            "uncategorized_products": product_counts[None],
            "categorized_percentage": str((Decimal(categorized) / total_products * Decimal("100")).quantize(Decimal("0.1"))) if total_products else "0.0",
            "observed_spend": _money(observed_total),
        },
        "categories": category_rows,
        "monthly_spend": monthly_spend,
    }
