"""Deterministic parser for Carrefour text-layer PDF receipts."""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from .base import ParsedReceipt, ParsedReceiptAdjustment, ParsedReceiptItem, ParsedReceiptVat, ReceiptParseError

_AMOUNT = r"-?\d+(?:\.\d{3})*,\d{2}"
_TOTAL = re.compile(rf"(?P<count>\d+)\s+ART\.\s+TOTAL\s+A\s+PAGAR\s*:\s*(?P<amount>{_AMOUNT})", re.I)
_SUBTOTAL = re.compile(rf"^SUBTOTAL\s+(?P<amount>{_AMOUNT})$", re.I)
_MULTIPLIER = re.compile(rf"^(?P<count>\d+)\s*x\s*\(\s*(?P<unit>{_AMOUNT})\s*\)\s*(?P<total>{_AMOUNT})$", re.I)
_ITEM_AMOUNT = re.compile(rf"^(?P<label>.+?)\s+(?P<amount>{_AMOUNT})$")
_CODE = re.compile(r"^(?P<name>.+?)\s+(?P<code>[A-Z]{1,3}\d{2,4})$")
_PROMO = re.compile(rf"^DESCUENTO\s+EN\s+2(?:ª|A)\s+UNIDAD\s+(?P<code>[A-Z]{{1,3}}\d{{2,4}})\s*(?P<amount>-{_AMOUNT[2:]})$", re.I)
_ADJUSTMENT = re.compile(rf"^(?P<label>DTO\.\s+(?:CUPON(?:\s+.*?)?|CHEQUE AHORRO))\s+(?P<amount>-{_AMOUNT[2:]})$", re.I)
_VAT = re.compile(rf"^(?P<rate>\d+[,.]\d{{2}})%\s+(?P<base>{_AMOUNT})\s+(?P<tax>{_AMOUNT})$")
_DATE = re.compile(r"\b(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})(?::\d{2})?\b")
_REF = re.compile(r"^NRF:\s*(\S+)", re.I)


def _money(value: str) -> Decimal:
    return Decimal(value.replace('.', '').replace(',', '.'))


def _label_code(value: str) -> tuple[str, str | None]:
    match = _CODE.fullmatch(value)
    return (match.group('name'), match.group('code')) if match else (value, None)


class CarrefourParser:
    """Parses items, line promotions, receipt-level coupons, VAT and receipt reference."""

    def parse(self, text: str) -> ParsedReceipt:
        lines = [' '.join(line.split()) for line in text.splitlines() if line.strip()]
        if not any('CENTROS COMERCIALES CARREFOUR' in line.upper() for line in lines[:8]):
            raise ReceiptParseError('El PDF no es un ticket Carrefour reconocido')
        total_match = next((match for line in lines if (match := _TOTAL.search(line))), None)
        if total_match is None:
            raise ReceiptParseError('No se ha encontrado el total de Carrefour')
        total = _money(total_match.group('amount'))
        expected_count = int(total_match.group('count'))
        date_match = next((match for line in lines if (match := _DATE.search(line))), None)
        if date_match is None:
            raise ReceiptParseError('No se ha encontrado la fecha y hora de compra')
        try:
            purchased_at = datetime.strptime(f"{date_match.group('date')} {date_match.group('time')}", '%d/%m/%Y %H:%M')
        except ValueError as exc:
            raise ReceiptParseError('Fecha de Carrefour inválida') from exc
        start = next((i + 1 for i, line in enumerate(lines[:15]) if len(line) >= 8 and set(line) == {'*'}), None)
        if start is None:
            raise ReceiptParseError('No se ha encontrado el comienzo de productos de Carrefour')
        end = next((i for i in range(start, len(lines)) if _SUBTOTAL.fullmatch(lines[i]) or _TOTAL.search(lines[i])), None)
        if end is None:
            raise ReceiptParseError('No se ha encontrado el final de productos de Carrefour')

        items: list[ParsedReceiptItem] = []
        codes: dict[str, list[int]] = {}
        warnings: list[str] = []
        i = start
        while i < end:
            line = lines[i]
            if set(line) in ({'='}, {'-'}) or not line:
                i += 1
                continue
            if line.upper().startswith('DESCUENTO'):
                match = _PROMO.fullmatch(line)
                if not match:
                    warnings.append(f'Descuento de producto no interpretado: {line}')
                elif not codes.get(match.group('code')):
                    warnings.append(f'Descuento sin producto asociado: {line}')
                else:
                    idx = codes[match.group('code')][-1]
                    item = items[idx]
                    discount = -_money(match.group('amount'))
                    if discount > (item.total_price or Decimal('0')):
                        warnings.append(f'Descuento superior al importe del producto: {line}')
                    else:
                        items[idx] = replace(
                            item, discount_amount=item.discount_amount + discount,
                            total_price=(item.total_price or Decimal('0')) - discount,
                            raw_text=f'{item.raw_text}\n{line}',
                        )
                i += 1
                continue
            match = _ITEM_AMOUNT.fullmatch(line)
            multiplier = _MULTIPLIER.fullmatch(lines[i + 1]) if i + 1 < end else None
            if multiplier is not None and not match:
                name, code = _label_code(line)
                quantity = Decimal(multiplier.group('count'))
                unit_price = _money(multiplier.group('unit'))
                gross = _money(multiplier.group('total'))
                if quantity * unit_price != gross:
                    warnings.append(f'Cantidad y precio no coinciden: {line}')
                raw = f'{line}\n{lines[i + 1]}'
                i += 2
            elif match:
                name, code = _label_code(match.group('label'))
                gross = _money(match.group('amount'))
                if gross < 0:
                    warnings.append(f'Importe de producto negativo no interpretado: {line}')
                    i += 1
                    continue
                quantity = Decimal('1')
                unit_price = gross
                raw = line
                i += 1
            else:
                warnings.append(f'Línea de producto no interpretada: {line}')
                i += 1
                continue
            if not name.strip():
                warnings.append(f'Nombre de producto vacío: {raw}')
                continue
            if len(name) > 255:
                warnings.append(f'Nombre demasiado largo: {raw}')
                continue
            idx = len(items)
            items.append(ParsedReceiptItem(
                raw_name=name, quantity=quantity, unit='ud', unit_price=unit_price,
                price_per_kg=None, total_price=gross, raw_text=raw,
                gross_total_price=gross,
            ))
            if code:
                codes.setdefault(code, []).append(idx)

        if not items:
            raise ReceiptParseError('No se ha podido interpretar ningún producto Carrefour')
        subtotal_match = next((match for line in lines if (match := _SUBTOTAL.fullmatch(line))), None)
        subtotal = _money(subtotal_match.group('amount')) if subtotal_match else None
        adjustments = []
        for line in lines[end:]:
            match = _ADJUSTMENT.fullmatch(line)
            if match:
                adjustments.append(ParsedReceiptAdjustment(
                    label=match.group('label'), amount=_money(match.group('amount')), raw_text=line,
                ))
            elif line.upper().startswith('DTO.'):
                warnings.append(f'Descuento general no interpretado: {line}')
        vat = []
        if any('TIPO BASE CUOTA' in line.upper() for line in lines):
            for line in lines:
                match = _VAT.fullmatch(line)
                if match:
                    vat.append(ParsedReceiptVat(
                        rate=_money(match.group('rate')), taxable_base=_money(match.group('base')),
                        tax_amount=_money(match.group('tax')), raw_text=line,
                    ))
        reference = next((match.group(1) for line in lines if (match := _REF.fullmatch(line))), None)
        counted = sum(int(item.quantity) for item in items if item.quantity is not None)
        if counted != expected_count:
            warnings.append(f'El ticket declara {expected_count} artículos y se han reconocido {counted}')
        net_lines = sum((item.total_price or Decimal('0') for item in items), Decimal('0'))
        expected_subtotal = subtotal if subtotal is not None else net_lines
        if abs(expected_subtotal - net_lines) > Decimal('0.01'):
            warnings.append(f'Los artículos suman {net_lines:.2f} €, pero el subtotal es {expected_subtotal:.2f} €')
        adjusted = expected_subtotal + sum((adj.amount for adj in adjustments), Decimal('0'))
        if abs(adjusted - total) > Decimal('0.01'):
            warnings.append(f'El subtotal menos descuentos es {adjusted:.2f} €, pero se pagaron {total:.2f} €')
        return ParsedReceipt(
            purchased_at=purchased_at, total=total, items=items, vat_breakdown=vat,
            warnings=warnings, subtotal=expected_subtotal, adjustments=adjustments,
            reference=reference,
        )
