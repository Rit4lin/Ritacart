"""Regression and API integration tests for the Carrefour manual import (sanitized fixtures)."""
from decimal import Decimal

import pytest

from app.parsers.base import ReceiptParseError
from app.parsers.carrefour import CarrefourParser
from app.services.pdf import _normalise_text
from app.services.importer import ReceiptImportError
from app.database import initialise_database
from sqlalchemy import inspect
from conftest import make_pdf


FIRST = """***Centros Comerciales Carrefour S.A***
Los Barrios
**************************************
CACAHUETE SIN SAL 0,99
CEREALES WEETABIX 4,79
FREJOL NEGRO FACUNDO
2 x ( 2,25 ) 4,50
GALLETAS TUC CRACKER 1,38
AVELLANA REPELADA 4,90
CASTAÑA GRANEL 4,29
CEBOLLA CARREFOUR 1,59
KAKI SHARONI 2,40
KIWI ZESPRI 2,65
NUEZ CASCARA GRANEL 3,10
PIMIENTO ITALIANO 3,31
TOMATE ENSALADA 1,17
MOLLETE CASARES 5UDS
2 x ( 1,99 ) 3,98
SUREÑA CASARES 10UD 1,89
BOLSA 48X60CM 0,15
JOGGER NINO OTTOMA 9,99
================================
18 ART. TOTAL A PAGAR : 51,08
TIPO BASE CUOTA
4,00% 23,44 0,94
10,00% 15,05 1,51
21,00% 8,38 1,76
06/10/2026 17:00:56
NRF: TEST-CARREFOUR-001
"""

SECOND = """***Centros Comerciales Carrefour S.A***
Los Barrios
**************************************
CASERA LIMON BIPACK 1,56
ARROZ THAI DF02
2 x ( 4,05 ) 8,10
DESCUENTO EN 2ª UNIDAD DF02 -2,03
CEREALES WEETABIX 4,79
FREJOL NEGRO FACUNDO
2 x ( 2,25 ) 4,50
INFUSION CACAO 3,09
INFUSION POMPADOUR 3,09
INFUSION TARTA QUESO 3,09
LASAÑA INSTANTANEA
2 x ( 1,62 ) 3,24
SAZONADOR PASTA 1,57
TOMATE TRITURADO DE31
2 x ( 1,20 ) 2,40
DESCUENTO EN 2ª UNIDAD DE31 -0,60
WEETABIX CHOCOLATE 6,05
MOZZARELLA CRF 200G E826
4 x ( 1,56 ) 6,24
DESCUENTO EN 2ª UNIDAD E826 -1,56
ALMENDRA REPELADA 4,65
ANACARDOS CRF150G 3,05
CEBOLLA CARREFOUR
2 x ( 1,59 ) 3,18
COL CHINA 3,85
DATIL NATURAL 1,99
PAPAYA DESHIDRATADA 2,89
PIMIENTO ITALIANO MA 2,44
PLATANO 1,97
SETA SHI TAKE AH57 3,56
SETA SHI TAKE AH57 3,46
DESCUENTO EN 2ª UNIDAD AH57 -1,76
DOTS ROLL BOMBÓN 2U 1,89
MOLLETE CASARES 5UDS
3 x ( 1,99 ) 5,97
HUEVO SUELO L 3,04
YAKINIKU ROLL 7,95
BANDEJA HORNO 39X29 6,99
================================
SUBTOTAL 98,65
DTO. CUPON 6X50 EUR -6,00
0000000000000
DTO. CHEQUE AHORRO -0,90
0000000000000
================================
37 ART. TOTAL A PAGAR : 91,75
TIPO BASE CUOTA
4,00% 41,31 1,65
10,00% 37,13 3,71
21,00% 6,57 1,38
22/10/2026 19:26:59
NRF: TEST-CARREFOUR-002
"""


@pytest.mark.parametrize(
    ("content", "total", "subtotal", "items", "units", "line_discount", "adjustment_amount"),
    [
        (FIRST, "51.08", "51.08", 16, 18, "0.00", "0.00"),
        (SECOND, "91.75", "98.65", 27, 37, "5.95", "-6.90"),
    ],
)
def test_complete_receipt_arithmetic(content, total, subtotal, items, units, line_discount, adjustment_amount):
    parsed = CarrefourParser().parse(_normalise_text(content))
    assert parsed.total == Decimal(total)
    assert parsed.subtotal == Decimal(subtotal)
    assert len(parsed.items) == items
    assert sum(item.quantity for item in parsed.items) == units
    assert sum(item.discount_amount for item in parsed.items) == Decimal(line_discount)
    assert sum(adj.amount for adj in parsed.adjustments) == Decimal(adjustment_amount)
    assert sum(item.total_price for item in parsed.items) == Decimal(subtotal)
    assert len(parsed.vat_breakdown) == 3
    assert parsed.warnings == []


def test_promotions_attach_to_correct_product_and_repeated_lines():
    parsed = CarrefourParser().parse(_normalise_text(SECOND))
    rice = next(item for item in parsed.items if item.raw_name == 'ARROZ THAI')
    assert (rice.quantity, rice.unit_price, rice.gross_total_price, rice.discount_amount, rice.total_price) == (
        Decimal('2'), Decimal('4.05'), Decimal('8.10'), Decimal('2.03'), Decimal('6.07'),
    )
    mushrooms = [item for item in parsed.items if item.raw_name == 'SETA SHI TAKE']
    assert len(mushrooms) == 2
    assert sum(item.total_price for item in mushrooms) == Decimal('5.26')
    assert mushrooms[-1].discount_amount == Decimal('1.76')
    assert [adj.label for adj in parsed.adjustments] == ['DTO. CUPON 6X50 EUR', 'DTO. CHEQUE AHORRO']
    assert parsed.reference == 'TEST-CARREFOUR-002'


def test_unknown_promotion_is_flagged_instead_of_silently_discarded():
    parsed = CarrefourParser().parse(_normalise_text(
        SECOND.replace('DESCUENTO EN 2ª UNIDAD DF02 -2,03', 'DESCUENTO ESPECIAL DF02 -2,03')
    ))
    assert any('Descuento de producto no interpretado' in warning for warning in parsed.warnings)
    assert any('subtotal' in warning for warning in parsed.warnings)


def test_rejects_other_stores_and_broken_receipts():
    with pytest.raises(ReceiptParseError):
        CarrefourParser().parse(FIRST.replace('Centros Comerciales Carrefour', 'Otro Comercio'))
    with pytest.raises(ReceiptParseError):
        CarrefourParser().parse(FIRST.replace('18 ART. TOTAL A PAGAR : 51,08', 'SIN TOTAL'))


def test_manual_import_and_reprocessing_are_store_specific(client, receipt_pdf):
    # Minimal PDF fixture avoids personal or payment details from the original receipts.
    content = """***Centros Comerciales Carrefour S.A***
**************************************
PAN DE MOLDE 1,90
1 ART. TOTAL A PAGAR : 1,90
08/10/2026 12:15:00
NRF: TEST-NRF-123
"""
    imported = client.post('/api/receipts/import', files={'file': ('carrefour.pdf', make_pdf(content), 'application/pdf')})
    assert imported.status_code == 201, imported.text
    data = imported.json()
    assert data['imported'] is True and data['duplicate'] is False
    receipt_id = data['receipt_id']
    record = client.get(f'/api/receipts/{receipt_id}').json()
    assert record['store'] == 'Carrefour'
    assert record['total'] == '1.90'
    assert record['reference'] == 'TEST-NRF-123'
    assert len(record['items']) == 1
    assert record['items'][0]['discount_amount'] == '0.00'

    again = client.post('/api/receipts/import', files={'file': ('renamed.pdf', make_pdf(content), 'application/pdf')})
    assert again.json()['duplicate'] is True
    assert again.json()['receipt_id'] == receipt_id
    # Distinct bytes with the same unique NRF must also be recognised as the same receipt.
    rewritten = make_pdf(content + '\nExportación alternativa')
    same_nrf = client.post('/api/receipts/import', files={'file': ('alternative.pdf', rewritten, 'application/pdf')})
    assert same_nrf.json()['duplicate'] is True
    assert same_nrf.json()['receipt_id'] == receipt_id
    assert client.post(f'/api/receipts/{receipt_id}/reprocess').status_code == 200
    assert client.get(f'/api/receipts/{receipt_id}').json()['store'] == 'Carrefour'

    mercadona = client.post('/api/receipts/import', files={'file': ('mercadona.pdf', receipt_pdf, 'application/pdf')})
    assert mercadona.status_code == 201, mercadona.text
    assert client.get(f"/api/receipts/{mercadona.json()['receipt_id']}").json()['store'] == 'Mercadona'


def test_carrefour_must_never_be_imported_from_email(client):
    content = """***Centros Comerciales Carrefour S.A***
**************************************
PAN 0,99
1 ART. TOTAL A PAGAR : 0,99
08/10/2026 12:15:00
NRF: TEST-EMAIL-REF
"""
    with pytest.raises(ReceiptImportError, match='solo está permitida para Mercadona'):
        client.app.state.importer.import_pdf(
            make_pdf(content), 'carrefour.pdf',
            source_message_id='<test-email@example.invalid>', source_attachment_index=0,
        )
    assert client.get('/api/receipts').json() == []


def test_existing_sqlite_receipts_survive_additive_v2_upgrade(client, receipt_pdf):
    imported = client.post(
        '/api/receipts/import',
        files={'file': ('old-mercadona.pdf', receipt_pdf, 'application/pdf')},
    )
    assert imported.status_code == 201
    receipt_id = imported.json()['receipt_id']
    engine = client.app.state.database_engine

    # Emulate the earlier schema on an otherwise populated local database.
    with engine.begin() as connection:
        connection.exec_driver_sql('DROP INDEX IF EXISTS ix_receipt_store_reference')
        connection.exec_driver_sql('ALTER TABLE receipts DROP COLUMN subtotal')
        connection.exec_driver_sql('ALTER TABLE receipts DROP COLUMN reference')
        connection.exec_driver_sql('ALTER TABLE receipt_items DROP COLUMN gross_total_price')
        connection.exec_driver_sql('ALTER TABLE receipt_items DROP COLUMN discount_amount')

    initialise_database(engine)
    assert {'subtotal', 'reference'}.issubset(
        {column['name'] for column in inspect(engine).get_columns('receipts')}
    )
    assert {'gross_total_price', 'discount_amount'}.issubset(
        {column['name'] for column in inspect(engine).get_columns('receipt_items')}
    )
    stored = client.get(f'/api/receipts/{receipt_id}')
    assert stored.status_code == 200
    data = stored.json()
    assert data['store'] == 'Mercadona'
    assert data['total'] == '3.25'
    assert len(data['items']) == 2
