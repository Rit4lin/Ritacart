from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .base import ParsedReceipt, ParsedReceiptItem, ReceiptParseError


_DATE_RE = re.compile(r"(?<!\d)(\d{2}[/-]\d{2}[/-]\d{4})(?:\s+(\d{2}:\d{2}))?")
_TIME_RE = re.compile(r"(?<!\d)(\d{2}:\d{2})(?!\d)")
_TOTAL_RE = re.compile(r"(?:TOTAL(?:\s+(?:A\s+PAGAR|COMPRA))?|IMPORTE\s+TOTAL)\D{0,20}(\d+[,.]\d{2})", re.I)
_UNIT_ITEM_RE = re.compile(
    r"^(\d+(?:[,.]\d+)?)\s+(.+?)\s+(\d+[,.]\d{2})\s+(\d+[,.]\d{2})$"
)
_WEIGHT_ITEM_RE = re.compile(
    r"^(\d+(?:[,.]\d+)?)\s*(kg|g)\s*(?:x|@)?\s*"
    r"(\d+[,.]\d{2})\s*(?:[^\w\s/])?\s*/?\s*(kg|g)\s+(\d+[,.]\d{2})$",
    re.I,
)


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except InvalidOperation as exc:
        raise ReceiptParseError(f"Valor decimal inválido: {value}") from exc


class MercadonaParser:
    """Deterministic parser for the embedded text of Mercadona digital receipts."""

    def parse(self, text: str) -> ParsedReceipt:
        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        if not lines:
            raise ReceiptParseError("El PDF no contiene texto extraíble")

        purchased_at = self._parse_date_time(lines)
        total = self._parse_total(lines)
        items, warnings = self._parse_items(lines)
        if not items:
            warnings.append("No se ha podido interpretar ninguna línea de producto")
        return ParsedReceipt(purchased_at=purchased_at, total=total, items=items, warnings=warnings)

    def _parse_date_time(self, lines: list[str]) -> datetime:
        joined = "\n".join(lines)
        date_match = _DATE_RE.search(joined)
        if not date_match:
            raise ReceiptParseError("No se ha encontrado fecha de compra")
        date_text, time_text = date_match.groups()
        if not time_text:
            time_match = _TIME_RE.search(joined)
            time_text = time_match.group(1) if time_match else "00:00"
        for format_string in ("%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(f"{date_text} {time_text}", format_string)
            except ValueError:
                continue
        raise ReceiptParseError(f"Fecha de compra inválida: {date_text} {time_text}")

    def _parse_total(self, lines: list[str]) -> Decimal:
        matches = _TOTAL_RE.findall("\n".join(lines))
        if not matches:
            raise ReceiptParseError("No se ha encontrado el total del ticket")
        return _decimal(matches[-1])

    def _parse_items(self, lines: list[str]) -> tuple[list[ParsedReceiptItem], list[str]]:
        items: list[ParsedReceiptItem] = []
        warnings: list[str] = []
        consumed: set[int] = set()

        for index, line in enumerate(lines):
            weighted = _WEIGHT_ITEM_RE.match(line)
            if weighted and index > 0:
                name = lines[index - 1]
                if not self._is_metadata(name):
                    quantity, unit, price_per_kg, _, line_total = weighted.groups()
                    items.append(
                        ParsedReceiptItem(
                            raw_name=name,
                            quantity=_decimal(quantity),
                            unit=unit.lower(),
                            unit_price=None,
                            price_per_kg=_decimal(price_per_kg),
                            total_price=_decimal(line_total),
                            raw_text=f"{name}\n{line}",
                        )
                    )
                    consumed.update({index - 1, index})
                    continue

            unit_item = _UNIT_ITEM_RE.match(line)
            if unit_item and not self._is_metadata(line):
                quantity, name, unit_price, line_total = unit_item.groups()
                items.append(
                    ParsedReceiptItem(
                        raw_name=name,
                        quantity=_decimal(quantity),
                        unit="ud",
                        unit_price=_decimal(unit_price),
                        price_per_kg=None,
                        total_price=_decimal(line_total),
                        raw_text=line,
                    )
                )
                consumed.add(index)

        for index, line in enumerate(lines):
            if index in consumed or self._is_metadata(line) or _TOTAL_RE.search(line):
                continue
            if any(token in line.upper() for token in ("MERCADONA", "TARJETA", "GRACIAS", "IVA")):
                continue
            warnings.append(f"Línea no interpretada: {line}")
        return items, warnings

    @staticmethod
    def _is_metadata(line: str) -> bool:
        return bool(_DATE_RE.search(line) or _TIME_RE.fullmatch(line) or _TOTAL_RE.search(line))
