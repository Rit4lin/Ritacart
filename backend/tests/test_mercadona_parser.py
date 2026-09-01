from decimal import Decimal

from app.parsers.mercadona import MercadonaParser

from conftest import RECEIPT_TEXT


def test_mercadona_parser_handles_unit_and_weight_items() -> None:
    parsed = MercadonaParser().parse(RECEIPT_TEXT)

    assert parsed.purchased_at.isoformat() == "2026-08-01T14:30:00"
    assert parsed.total == Decimal("3.25")
    assert len(parsed.items) == 2
    unit_item, weighted_item = parsed.items
    assert unit_item.raw_name == "LIMÓN ZERO 2L"
    assert unit_item.quantity == Decimal("2")
    assert unit_item.unit_price == Decimal("0.95")
    assert unit_item.total_price == Decimal("1.90")
    assert weighted_item.raw_name == "PERA CONFERENCIA"
    assert weighted_item.quantity == Decimal("0.490")
    assert weighted_item.unit == "kg"
    assert weighted_item.price_per_kg == Decimal("2.75")
    assert weighted_item.total_price == Decimal("1.35")


def test_mercadona_parser_reports_unparsed_lines() -> None:
    parsed = MercadonaParser().parse(RECEIPT_TEXT + "LÍNEA DESCONOCIDA\n")

    assert "Línea no interpretada: LÍNEA DESCONOCIDA" in parsed.warnings
