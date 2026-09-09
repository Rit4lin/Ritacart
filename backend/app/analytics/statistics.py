from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Receipt

StatisticsRange = Literal["3m", "6m", "1y", "all"]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _month_start(value: datetime) -> datetime:
    return datetime(value.year, value.month, 1)


def _add_months(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    return datetime(index // 12, index % 12 + 1, 1)


def _range_start(now: datetime, selected_range: StatisticsRange) -> datetime | None:
    current_month = _month_start(now)
    if selected_range == "3m":
        return _add_months(current_month, -2)
    if selected_range == "6m":
        return _add_months(current_month, -5)
    if selected_range == "1y":
        return _add_months(current_month, -11)
    return None


def _comparison(current: Decimal, previous: Decimal) -> dict[str, str | None]:
    difference = current - previous
    return {
        "current": _money(current),
        "previous": _money(previous),
        "difference": _money(difference),
        "percentage_change": str((difference / previous * Decimal("100")).quantize(Decimal("0.1")))
        if previous
        else None,
    }


def _local_now(timezone: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def global_statistics(
    session: Session,
    selected_range: StatisticsRange,
    timezone: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build global shopping statistics directly from receipt observations."""
    reference = now or _local_now(timezone)
    start = _range_start(reference, selected_range)
    all_receipts = session.scalars(select(Receipt).order_by(Receipt.purchased_at)).all()
    receipts = [receipt for receipt in all_receipts if start is None or receipt.purchased_at >= start]

    spend = sum((receipt.total for receipt in receipts), Decimal("0"))
    receipt_count = len(receipts)
    average_basket = spend / receipt_count if receipt_count else Decimal("0")
    intervals = [
        (later.purchased_at - earlier.purchased_at).total_seconds() / 86400
        for earlier, later in zip(receipts, receipts[1:])
    ]
    average_interval = (
        sum((Decimal(str(interval)) for interval in intervals), Decimal("0")) / len(intervals)
        if intervals
        else None
    )

    effective_start = start or (receipts[0].purchased_at if receipts else None)
    period_end = reference if start is not None else (receipts[-1].purchased_at if len(receipts) > 1 else None)
    covered_days = (period_end - effective_start).total_seconds() / 86400 if effective_start and period_end else 0
    covered_weeks = Decimal(str(covered_days)) / Decimal("7") if covered_days > 0 else Decimal("0")
    weekly_spend = spend / covered_weeks if covered_weeks else Decimal("0")

    month_values: dict[str, list[Decimal | int]] = {}
    if effective_start:
        cursor = _month_start(effective_start)
        last_month = _month_start(period_end or reference)
        while cursor <= last_month:
            month_values[cursor.strftime("%Y-%m")] = [Decimal("0"), 0]
            cursor = _add_months(cursor, 1)
    for receipt in receipts:
        values = month_values.setdefault(receipt.purchased_at.strftime("%Y-%m"), [Decimal("0"), 0])
        values[0] += receipt.total  # type: ignore[operator]
        values[1] += 1  # type: ignore[operator]

    weekdays = [0] * 7
    hours = [0] * 24
    for receipt in receipts:
        weekdays[receipt.purchased_at.weekday()] += 1
        hours[receipt.purchased_at.hour] += 1

    month_start = _month_start(reference)
    previous_month_start = _add_months(month_start, -1)
    year_start = datetime(reference.year, 1, 1)
    previous_year_start = datetime(reference.year - 1, 1, 1)
    month_current = sum((r.total for r in all_receipts if month_start <= r.purchased_at < _add_months(month_start, 1)), Decimal("0"))
    month_previous = sum((r.total for r in all_receipts if previous_month_start <= r.purchased_at < month_start), Decimal("0"))
    year_current = sum((r.total for r in all_receipts if year_start <= r.purchased_at < datetime(reference.year + 1, 1, 1)), Decimal("0"))
    year_previous = sum((r.total for r in all_receipts if previous_year_start <= r.purchased_at < year_start), Decimal("0"))

    return {
        "range": selected_range,
        "period": {
            "total_spend": _money(spend),
            "receipt_count": receipt_count,
            "average_basket": _money(average_basket),
            "average_weekly_spend": _money(weekly_spend),
            "average_days_between_shops": str(average_interval.quantize(Decimal("0.1"))) if average_interval is not None else None,
        },
        "comparisons": {"current_month": _comparison(month_current, month_previous), "current_year": _comparison(year_current, year_previous)},
        "monthly_spend": [
            {"month": month, "total_spend": _money(values[0]), "receipt_count": values[1], "average_basket": _money(values[0] / values[1]) if values[1] else "0.00"}
            for month, values in month_values.items()
        ],
        "purchases_by_weekday": [{"weekday": index + 1, "receipt_count": count} for index, count in enumerate(weekdays)],
        "purchases_by_hour": [{"hour": hour, "receipt_count": count} for hour, count in enumerate(hours)],
    }
