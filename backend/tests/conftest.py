from __future__ import annotations

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


RECEIPT_TEXT = """MERCADONA
01/08/2026 14:30
2 LIMÓN ZERO 2L 0,95 1,90
PERA CONFERENCIA
0,490 kg 2,75 €/kg 1,35
TOTAL 3,25
"""


COLUMN_LAYOUT_RECEIPT_TEXT = """MERCADONA
01/08/2026 14:30
Descripción
P. Unit
Importe
1 BEBIDA VEGETAL
6,60
2 REFRESCO SIN AZÚCAR
0,95
1,90
1 QUESO FRESCO
2,61
1 PERA DE TEMPORADA
0,490 kg
2,75 €/kg
1,35
TOTAL (€)
12,46
TARJETA BANCARIA
12,46
IVA
BASE IMPONIBLE (€)
CUOTA (€)
4%
2,50
0,10
10%
5,00
0,50
21%
3,60
0,76
TOTAL
11,10
1,36
"""


def make_pdf(text: str = RECEIPT_TEXT) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    content = document.tobytes()
    document.close()
    return content


@pytest.fixture
def receipt_pdf() -> bytes:
    return make_pdf()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'ritacart.db').as_posix()}")
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    with TestClient(create_app()) as test_client:
        yield test_client
