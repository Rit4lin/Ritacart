from decimal import Decimal

from app.parsers.mercadona import MercadonaParser

from conftest import COLUMN_LAYOUT_RECEIPT_TEXT, RECEIPT_TEXT


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


def test_mercadona_parser_handles_column_layout_and_vat_breakdown() -> None:
    parsed = MercadonaParser().parse(COLUMN_LAYOUT_RECEIPT_TEXT)

    assert parsed.total == Decimal("12.46")
    assert [item.raw_name for item in parsed.items] == [
        "BEBIDA VEGETAL",
        "REFRESCO SIN AZÚCAR",
        "QUESO FRESCO",
        "PERA DE TEMPORADA",
    ]
    assert parsed.items[1].quantity == Decimal("2")
    assert parsed.items[1].unit_price == Decimal("0.95")
    assert parsed.items[1].total_price == Decimal("1.90")
    assert parsed.items[3].quantity == Decimal("0.490")
    assert parsed.items[3].unit == "kg"
    assert parsed.items[3].price_per_kg == Decimal("2.75")
    assert parsed.items[3].total_price == Decimal("1.35")
    assert [(vat.rate, vat.taxable_base, vat.tax_amount) for vat in parsed.vat_breakdown] == [
        (Decimal("4"), Decimal("2.50"), Decimal("0.10")),
        (Decimal("10"), Decimal("5.00"), Decimal("0.50")),
        (Decimal("21"), Decimal("3.60"), Decimal("0.76")),
    ]
