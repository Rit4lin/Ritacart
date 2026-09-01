from __future__ import annotations

import imaplib
from email.message import EmailMessage
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.database import create_database_engine, get_session_factory, initialise_database
from app import models  # noqa: F401
from app.services.importer import ReceiptImportError, ReceiptImportService

from conftest import make_pdf


class FakeImap:
    def __init__(self, raw_message: bytes):
        self.raw_message = raw_message

    def login(self, username: str, password: str):
        return "OK", []

    def select(self, folder: str, readonly: bool = False):
        return "OK", [b"1"]

    def search(self, *args):
        return "OK", [b"1"]

    def fetch(self, number: bytes, query: str):
        return "OK", [(b"1 (RFC822)", self.raw_message)]

    def logout(self):
        return "BYE", []


def _service(tmp_path, monkeypatch) -> ReceiptImportService:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'ritacart.db').as_posix()}")
    monkeypatch.setenv("EMAIL_USERNAME", "user@example.test")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-password")
    settings = get_settings()
    engine = create_database_engine(settings)
    initialise_database(engine)
    return ReceiptImportService(settings, get_session_factory(engine))


def _email_with_pdf(pdf_bytes: bytes) -> bytes:
    message = EmailMessage()
    message["Message-ID"] = "<mercadona-1@example.test>"
    message["From"] = "ticket_digital@mail.mercadona.com"
    message.set_content("Ticket adjunto")
    message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="ticket.pdf")
    return message.as_bytes()


def test_imap_importer_uses_message_id_and_pdf_attachment(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path, monkeypatch)
    fake = FakeImap(_email_with_pdf(make_pdf()))
    with patch("app.services.importer.imaplib.IMAP4_SSL", return_value=fake):
        assert service.run_imap_import() == 1
        assert service.run_imap_import() == 0

    status = service.get_status()
    assert status["last_error"] is None
    assert status["imported_receipts_last_run"] == 0


def test_imap_connection_failure_is_reported(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path, monkeypatch)
    with patch(
        "app.services.importer.imaplib.IMAP4_SSL",
        side_effect=imaplib.IMAP4.error("connection failed"),
    ):
        with pytest.raises(ReceiptImportError):
            service.run_imap_import()

    assert service.get_status()["last_error"] == "connection failed"


def test_app_status_without_gmail_credentials(client) -> None:
    response = client.get("/api/import/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
