from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Product, ReceiptItem
from .statistics import _add_months, _month_start


def _money(value: Decimal | None) -> str | None:
    return str(value.quantize(Decimal("0.01"))) if value is not None else None


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    return ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _category(product: Product) -> dict[str, object] | None:
    return {"id": product.category.id, "name": product.category.name, "slug": product.category.slug} if product.category else None


def _price(item: ReceiptItem) -> tuple[Decimal | None, str]:
    if item.price_per_kg is not None:
        return item.price_per_kg, "€/kg"
    if item.unit_price is not None:
        return item.unit_price, "€/ud"
    if item.total_price is not None and item.quantity not in (None, Decimal("0")):
        return item.total_price / item.quantity, "€/ud"
    return None, "€/ud"


def _daily_prices(product: Product) -> dict[tuple[str, str], Decimal]:
    result: dict[tuple[str, str], Decimal] = {}
    for item in product.receipt_items:
        price, unit = _price(item)
        if price is not None:
            key = (item.receipt.purchased_at.date().isoformat(), unit)
            result[key] = max(result.get(key, price), price)
    return result


def _product_fact(product: Product, now: datetime) -> dict[str, object] | None:
    receipts = {item.receipt_id: item.receipt.purchased_at for item in product.receipt_items}
    dates = sorted({purchased_at.date() for purchased_at in receipts.values()})
    if not dates:
        return None
    intervals = [Decimal((later - earlier).days) for earlier, later in zip(dates, dates[1:])]
    average = sum(intervals, Decimal("0")) / len(intervals) if intervals else None
    median = _median(intervals)
    variability = (
        sum((abs(interval - median) for interval in intervals), Decimal("0")) / len(intervals) / median
        if intervals and median and median > 0 else None
    )
    prices = _daily_prices(product)
    candidates = [(date, unit, price) for (date, unit), price in prices.items()]
    latest = max(candidates, default=None)
    quantities = [item.quantity for item in product.receipt_items if item.quantity is not None and item.quantity > 0]
    typical_quantity = _median(quantities)  # type: ignore[arg-type]
    total_spend = sum((item.total_price for item in product.receipt_items if item.total_price is not None), Decimal("0"))
    last = max(receipts.values())
    return {
        "product_id": product.id, "name": product.name, "category": _category(product),
        "purchase_count": len(receipts), "first_purchased_at": min(receipts.values()).isoformat(),
        "last_purchased_at": last.isoformat(), "days_since_last_purchase": (now.date() - last.date()).days,
        "average_days_between_purchases": str(average.quantize(Decimal("0.1"))) if average is not None else None,
        "median_days_between_purchases": str(median.quantize(Decimal("0.1"))) if median is not None else None,
        "relative_interval_variability": str(variability.quantize(Decimal("0.1"))) if variability is not None else None,
        "typical_quantity": str(typical_quantity) if typical_quantity is not None else None,
        "current_price": _money(latest[2]) if latest else None, "price_unit": latest[1] if latest else None,
        "total_spend": _money(total_spend), "daily_prices": prices,
    }


def _is_regular(fact: dict[str, object]) -> bool:
    variability = fact["relative_interval_variability"]
    return fact["purchase_count"] >= 3 and variability is not None and Decimal(str(variability)) <= Decimal("0.5")


def _public(fact: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in fact.items() if key != "daily_prices"}


def _basket_history(basket: list[dict[str, object]], now: datetime) -> list[dict[str, object]]:
    first_dates = [date for fact in basket for date, _ in fact["daily_prices"].keys()]  # type: ignore[union-attr]
    if not first_dates:
        return []
    cursor = _month_start(datetime.fromisoformat(min(first_dates)))
    end = _month_start(now)
    history: list[dict[str, object]] = []
    while cursor <= end:
        month_end = _add_months(cursor, 1).date().isoformat()
        cost = Decimal("0")
        covered = 0
        for fact in basket:
            prices = [(date, price) for (date, unit), price in fact["daily_prices"].items() if unit == fact["price_unit"] and date < month_end]  # type: ignore[union-attr]
            quantity = Decimal(str(fact["typical_quantity"] or "0"))
            if prices and quantity:
                cost += max(prices)[1] * quantity
                covered += 1
        history.append({"month": cursor.strftime("%Y-%m"), "cost": _money(cost), "coverage": str((Decimal(covered) / len(basket)).quantize(Decimal("0.01")))})
        cursor = _add_months(cursor, 1)
    return history


def basket_insights(session: Session, now: datetime) -> dict[str, object]:
    products = session.scalars(select(Product).options(
        selectinload(Product.category), selectinload(Product.receipt_items).selectinload(ReceiptItem.receipt)
    )).all()
    facts = [fact for product in products if (fact := _product_fact(product, now)) is not None]
    regular = [fact for fact in facts if _is_regular(fact)]
    active_regular = [fact for fact in regular if Decimal(str(fact["days_since_last_purchase"])) < Decimal(str(fact["median_days_between_purchases"])) * 2]
    basket = [fact for fact in active_regular if fact["current_price"] is not None and fact["typical_quantity"] is not None]
    basket.sort(key=lambda fact: (Decimal(str(fact["median_days_between_purchases"])), -int(fact["purchase_count"])))
    basket = basket[:20]
    current_cost = sum((Decimal(str(fact["current_price"])) * Decimal(str(fact["typical_quantity"])) for fact in basket), Decimal("0"))
    history = _basket_history(basket, now)
    sufficient = [point for point in history if Decimal(str(point["coverage"])) >= Decimal("0.70") and Decimal(str(point["cost"])) > 0]
    inflation = None
    if sufficient and basket:
        baseline = sufficient[0]
        baseline_cost = Decimal(str(baseline["cost"]))
        change = current_cost - baseline_cost
        inflation = {"baseline_month": baseline["month"], "baseline_cost": _money(baseline_cost), "current_cost": _money(current_cost), "change_absolute": _money(change), "change_percent": str((change / baseline_cost * Decimal("100")).quantize(Decimal("0.1"))), "coverage_current": "1.00", "coverage_baseline": baseline["coverage"]}
    comparisons: dict[str, dict[str, object] | None] = {}
    current_month = _month_start(now)
    for key, months in (("1m", 1), ("3m", 3), ("1y", 12)):
        target = _add_months(current_month, -months).strftime("%Y-%m")
        point = next((entry for entry in history if entry["month"] == target and Decimal(str(entry["coverage"])) >= Decimal("0.70")), None)
        previous = Decimal(str(point["cost"])) if point and Decimal(str(point["cost"])) else None
        comparisons[key] = {"month": target, "cost": _money(previous), "change_absolute": _money(current_cost - previous), "change_percent": str(((current_cost - previous) / previous * Decimal("100")).quantize(Decimal("0.1"))), "coverage": point["coverage"]} if previous else None
    due = []
    inactive = []
    for fact in regular:
        median = Decimal(str(fact["median_days_between_purchases"]))
        ratio = Decimal(str(fact["days_since_last_purchase"])) / median if median else Decimal("0")
        if ratio >= 2:
            inactive.append({**_public(fact), "status": "inactivo", "ratio": str(ratio.quantize(Decimal("0.1")))})
        elif ratio >= Decimal("0.75"):
            status = "pronto" if ratio < 1 else "toca" if ratio < Decimal("1.5") else "retrasado"
            due.append({**_public(fact), "status": status, "ratio": str(ratio.quantize(Decimal("0.1")))})
    due.sort(key=lambda fact: Decimal(str(fact["ratio"])), reverse=True)
    inactive.sort(key=lambda fact: Decimal(str(fact["ratio"])), reverse=True)
    recent_cutoff = now.date().toordinal() - 30
    new = [fact for fact in facts if datetime.fromisoformat(str(fact["first_purchased_at"])).date().toordinal() >= recent_cutoff]
    new.sort(key=lambda fact: str(fact["first_purchased_at"]), reverse=True)
    regular.sort(key=lambda fact: (Decimal(str(fact["median_days_between_purchases"])), -int(fact["purchase_count"])))
    return {"basket": {"items": [_public(fact) for fact in basket], "current_basket_cost": _money(current_cost), "basket_price_history": history, "personal_inflation": inflation, "basket_comparisons": comparisons}, "due_soon_products": due, "inactive_regular_products": inactive, "most_regular_products": [_public(fact) for fact in regular[:10]], "new_products": [_public(fact) for fact in new[:10]]}
