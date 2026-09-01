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
