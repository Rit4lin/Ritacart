from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .base import ParsedReceipt, ParsedReceiptItem, ParsedReceiptVat, ReceiptParseError


_DATE_RE = re.compile(r"(?<!\d)(\d{2}[/-]\d{2}[/-]\d{4})(?:\s+(\d{2}:\d{2}))?")
_TIME_RE = re.compile(r"(?<!\d)(\d{2}:\d{2})(?!\d)")
_TOTAL_RE = re.compile(r"(?:TOTAL(?:\s+(?:A\s+PAGAR|COMPRA))?|IMPORTE\s+TOTAL)\D{0,20}(\d+[,.]\d{2})", re.I)
_TOTAL_INLINE_RE = re.compile(
    r"^TOTAL(?:\s*\([^)]*\)|\s+(?:A\s+PAGAR|COMPRA))?\s+(\d+[,.]\d{2})$", re.I
)
_TOTAL_LABEL_RE = re.compile(
    r"^TOTAL(?:\s*\([^)]*\)|\s+(?:A\s+PAGAR|COMPRA))?$", re.I
)
_UNIT_ITEM_RE = re.compile(
    r"^(\d+(?:[,.]\d+)?)\s+(.+?)\s+(\d+[,.]\d{2})\s+(\d+[,.]\d{2})$"
)
_WEIGHT_ITEM_RE = re.compile(
    r"^(\d+(?:[,.]\d+)?)\s*(kg|g)\s*(?:x|@)?\s*"
    r"(\d+[,.]\d{2})\s*(?:[^\w\s/])?\s*/?\s*(kg|g)\s+(\d+[,.]\d{2})$",
    re.I,
)
_PRODUCT_LINE_RE = re.compile(r"^(\d+(?:[,.]\d+)?)\s+(.+)$")
_MONEY_RE = re.compile(r"^(\d+[,.]\d{2})$")
_WEIGHT_QUANTITY_RE = re.compile(r"^(\d+(?:[,.]\d+)?)\s*(kg|g)$", re.I)
_PRICE_PER_WEIGHT_RE = re.compile(
    r"^(\d+[,.]\d{2})\s*(?:[^\w\s/])?\s*/?\s*(kg|g)$", re.I
)
_VAT_RATE_RE = re.compile(r"^(\d+(?:[,.]\d+)?)\s*%$")


def _decimal(value: str) -> Decimal:
    try:
        normalized = value.replace(" ", "")
        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        return Decimal(normalized)
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
        vat_breakdown = self._parse_vat_breakdown(lines)
        if not items:
            warnings.append("No se ha podido interpretar ninguna línea de producto")
        return ParsedReceipt(
            purchased_at=purchased_at,
            total=total,
            items=items,
            vat_breakdown=vat_breakdown,
            warnings=warnings,
        )

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
        for index, line in enumerate(lines):
            inline_match = _TOTAL_INLINE_RE.fullmatch(line)
            if inline_match:
                return _decimal(inline_match.group(1))
            if _TOTAL_LABEL_RE.fullmatch(line):
                for candidate in lines[index + 1 : index + 4]:
                    money_match = _MONEY_RE.fullmatch(candidate)
                    if money_match:
                        return _decimal(money_match.group(1))
        matches = _TOTAL_RE.findall("\n".join(lines))
        if not matches:
            raise ReceiptParseError("No se ha encontrado el total del ticket")
        return _decimal(matches[0])

    def _parse_items(self, lines: list[str]) -> tuple[list[ParsedReceiptItem], list[str]]:
        item_lines = self._item_section(lines)
        if item_lines is not None:
            return self._parse_column_items(item_lines)

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
    def _item_section(lines: list[str]) -> list[str] | None:
        start = next(
            (index for index, line in enumerate(lines) if line.casefold().startswith("descripci")),
            None,
        )
        if start is None:
            return None
        end = next(
            (
                index
                for index in range(start + 1, len(lines))
                if _TOTAL_LABEL_RE.fullmatch(lines[index]) or _TOTAL_INLINE_RE.fullmatch(lines[index])
            ),
            None,
        )
        return lines[start + 1 : end] if end is not None else None

    def _parse_column_items(self, lines: list[str]) -> tuple[list[ParsedReceiptItem], list[str]]:
        items: list[ParsedReceiptItem] = []
        warnings: list[str] = []
        consumed: set[int] = set()

        for index, line in enumerate(lines):
            if index in consumed:
                continue
            product_match = _PRODUCT_LINE_RE.match(line)
            if not product_match:
                continue
            quantity, name = product_match.groups()

            if index + 3 < len(lines):
                weight_match = _WEIGHT_QUANTITY_RE.fullmatch(lines[index + 1])
                price_per_weight_match = _PRICE_PER_WEIGHT_RE.fullmatch(lines[index + 2])
                line_total_match = _MONEY_RE.fullmatch(lines[index + 3])
                if weight_match and price_per_weight_match and line_total_match:
                    weight, unit = weight_match.groups()
                    price_per_kg, _ = price_per_weight_match.groups()
                    items.append(
                        ParsedReceiptItem(
                            raw_name=name,
                            quantity=_decimal(weight),
                            unit=unit.lower(),
                            unit_price=None,
                            price_per_kg=_decimal(price_per_kg),
                            total_price=_decimal(line_total_match.group(1)),
                            raw_text="\n".join(lines[index : index + 4]),
                        )
                    )
                    consumed.update(range(index, index + 4))
                    continue

            if index + 1 >= len(lines):
                continue
            first_price = _MONEY_RE.fullmatch(lines[index + 1])
            second_price = (
                _MONEY_RE.fullmatch(lines[index + 2]) if index + 2 < len(lines) else None
            )
            if not first_price:
                continue
            unit_price = _decimal(first_price.group(1)) if second_price else None
            line_total = _decimal(second_price.group(1) if second_price else first_price.group(1))
            if unit_price is None and _decimal(quantity) == Decimal("1"):
                unit_price = line_total
            items.append(
                ParsedReceiptItem(
                    raw_name=name,
                    quantity=_decimal(quantity),
                    unit="ud",
                    unit_price=unit_price,
                    price_per_kg=None,
                    total_price=line_total,
                    raw_text="\n".join(lines[index : index + (3 if second_price else 2)]),
                )
            )
            consumed.update(range(index, index + (3 if second_price else 2)))

        for index, line in enumerate(lines):
            if index in consumed or self._is_item_heading(line):
                continue
            warnings.append(f"Línea no interpretada: {line}")
        return items, warnings

    @staticmethod
    def _parse_vat_breakdown(lines: list[str]) -> list[ParsedReceiptVat]:
        vat_start = next((index for index, line in enumerate(lines) if line.upper() == "IVA"), None)
        if vat_start is None:
            return []
        breakdown: list[ParsedReceiptVat] = []
        for index in range(vat_start + 1, len(lines) - 2):
            rate_match = _VAT_RATE_RE.fullmatch(lines[index])
            base_match = _MONEY_RE.fullmatch(lines[index + 1])
            amount_match = _MONEY_RE.fullmatch(lines[index + 2])
            if rate_match and base_match and amount_match:
                breakdown.append(
                    ParsedReceiptVat(
                        rate=_decimal(rate_match.group(1)),
                        taxable_base=_decimal(base_match.group(1)),
                        tax_amount=_decimal(amount_match.group(1)),
                        raw_text="\n".join(lines[index : index + 3]),
                    )
                )
        return breakdown

    @staticmethod
    def _is_metadata(line: str) -> bool:
        return bool(_DATE_RE.search(line) or _TIME_RE.fullmatch(line) or _TOTAL_RE.search(line))

    @staticmethod
    def _is_item_heading(line: str) -> bool:
        return line.casefold() in {"p. unit", "importe"}
