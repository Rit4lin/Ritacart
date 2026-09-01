from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ParsedReceiptItem:
    raw_name: str
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    price_per_kg: Decimal | None
    total_price: Decimal | None
    raw_text: str


@dataclass(frozen=True)
class ParsedReceiptVat:
    rate: Decimal
    taxable_base: Decimal
    tax_amount: Decimal
    raw_text: str


@dataclass(frozen=True)
class ParsedReceipt:
    purchased_at: datetime
    total: Decimal
    items: list[ParsedReceiptItem]
    vat_breakdown: list[ParsedReceiptVat] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ReceiptParseError(ValueError):
    """Raised when the document cannot be identified as a usable receipt."""
