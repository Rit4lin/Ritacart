from __future__ import annotations

import hashlib
import imaplib
import json
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from email import message_from_bytes
from email.message import Message
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from ..config import Settings
from ..models import Product, ProductAlias, Receipt, ReceiptItem, ReceiptVat, Store
from ..parsers.base import ParsedReceipt, ParsedReceiptItem, ParsedReceiptVat
from ..parsers.mercadona import MercadonaParser
from .pdf import PdfExtractionError, extract_text

logger = logging.getLogger(__name__)


class ReceiptImportError(ValueError):
    """Raised when a receipt cannot be safely imported."""


@dataclass(frozen=True)
class ImportResult:
    receipt_id: int | None
    imported: bool
    duplicate: bool
    warnings: list[str]


@dataclass
class ImportStatus:
    enabled: bool
    last_run: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    imported_receipts_last_run: int = 0

    def public(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "imported_receipts_last_run": self.imported_receipts_last_run,
        }


class ReceiptImportService:
    def __init__(self, settings: Settings, session_factory: sessionmaker[Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.parser = MercadonaParser()
        self._status = ImportStatus(enabled=settings.email_enabled)
        self._status_lock = threading.Lock()

    def get_status(self) -> dict[str, object]:
        with self._status_lock:
            return self._status.public()

    def import_pdf(
        self,
        pdf_bytes: bytes,
        source_filename: str | None,
        source_message_id: str | None = None,
        source_attachment_index: int | None = None,
    ) -> ImportResult:
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        with self.session_factory() as session:
            existing = session.scalar(
                select(Receipt).where(Receipt.source_file_hash == file_hash)
            )
            if existing:
                return self._duplicate_result(session, existing)
            if source_message_id is not None and source_attachment_index is not None:
                existing = session.scalar(
                    select(Receipt).where(
                        Receipt.source_message_id == source_message_id,
                        Receipt.source_attachment_index == source_attachment_index,
                    )
                )
                if existing:
                    return self._duplicate_result(session, existing)

            try:
                extracted_text = extract_text(pdf_bytes)
                parsed = self.parser.parse(extracted_text)
            except (PdfExtractionError, ValueError) as exc:
                raise ReceiptImportError(str(exc)) from exc

            semantic_duplicate = self._find_semantic_duplicate(session, parsed)
            if semantic_duplicate is not None:
                return self._duplicate_result(session, semantic_duplicate)

            pdf_path = self._save_pdf(pdf_bytes, file_hash)
            store = self._get_or_create_store(session)
            receipt = Receipt(
                store=store,
                purchased_at=parsed.purchased_at,
                total=parsed.total,
                source_message_id=source_message_id,
                source_attachment_index=source_attachment_index,
                source_filename=self._display_filename(source_filename),
                source_file_hash=file_hash,
                source_pdf_path=str(pdf_path),
                source_extracted_text=extracted_text,
                parser_warnings=json.dumps(parsed.warnings, ensure_ascii=False),
            )
            session.add(receipt)
            for item in parsed.items:
                self._append_item(session, receipt, store, item)
            self._append_vat_breakdown(receipt, parsed.vat_breakdown)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(Receipt).where(Receipt.source_file_hash == file_hash))
                if existing:
                    return self._duplicate_result(session, existing)
                raise
            session.refresh(receipt)
            return ImportResult(
                receipt.id, imported=True, duplicate=False, warnings=parsed.warnings
            )

    def reprocess_receipt(self, receipt_id: int) -> ImportResult:
        """Re-extract the preserved PDF and rebuild its normalized observations."""
        with self.session_factory() as session:
            receipt = session.get(Receipt, receipt_id)
            if receipt is None:
                raise ReceiptImportError("Ticket no encontrado")

            pdf_path = self.settings.app_data_dir / "receipts" / f"{receipt.source_file_hash}.pdf"
            try:
                if pdf_path.is_file():
                    extracted_text = extract_text(pdf_path.read_bytes())
                elif receipt.source_extracted_text:
                    extracted_text = receipt.source_extracted_text
                else:
                    raise ReceiptImportError(
                        "El ticket no conserva ni el PDF original ni texto extraído para reprocesarlo"
                    )
                parsed = self.parser.parse(extracted_text)
            except (OSError, PdfExtractionError, ValueError) as exc:
                if isinstance(exc, ReceiptImportError):
                    raise
                raise ReceiptImportError(str(exc)) from exc

            receipt.source_extracted_text = extracted_text
            self._replace_normalized_data(session, receipt, parsed)
            session.commit()
            return ImportResult(
                receipt.id,
                imported=True,
                duplicate=False,
                warnings=parsed.warnings,
            )

    def run_imap_import(self) -> int:
        """Fetch configured Mercadona PDF attachments once, without marking mail read."""
        started_at = datetime.now(UTC)
        self._set_status(last_run=started_at, imported_receipts_last_run=0, last_error=None)
        if not self.settings.email_enabled:
            logger.info("Email importer disabled: EMAIL_USERNAME or EMAIL_PASSWORD is not configured")
            return 0

        imported = 0
        try:
            client = self._connect_imap()
            try:
                status, _ = client.select(self.settings.email_folder, readonly=True)
                if status != "OK":
                    raise ReceiptImportError(f"No se ha podido abrir {self.settings.email_folder}")
                status, message_ids = client.search(None, "FROM", self.settings.email_receipt_sender)
                if status != "OK":
                    raise ReceiptImportError("No se ha podido buscar mensajes en IMAP")
                for message_number in (message_ids[0].split() if message_ids else []):
                    imported += self._import_message(client, message_number)
            finally:
                try:
                    client.logout()
                except imaplib.IMAP4.error:
                    pass
        except (imaplib.IMAP4.error, OSError, ReceiptImportError) as exc:
            self._set_status(last_error=str(exc), imported_receipts_last_run=imported)
            logger.exception("IMAP receipt import failed")
            raise ReceiptImportError(str(exc)) from exc

        completed_at = datetime.now(UTC)
        self._set_status(
            last_success=completed_at,
            last_error=None,
            imported_receipts_last_run=imported,
        )
        return imported

    def _connect_imap(self) -> imaplib.IMAP4:
        if not self.settings.email_use_ssl:
            raise ReceiptImportError("EMAIL_USE_SSL debe estar habilitado para IMAP")
        client = imaplib.IMAP4_SSL(self.settings.email_host, self.settings.email_port)
        client.login(self.settings.email_username, self.settings.email_password)
        return client

    def _import_message(self, client: imaplib.IMAP4, message_number: bytes) -> int:
        status, payload = client.fetch(message_number, "(RFC822)")
        if status != "OK" or not payload:
            raise ReceiptImportError("No se ha podido descargar un mensaje IMAP")
        raw_message = next(
            (part[1] for part in payload if isinstance(part, tuple) and isinstance(part[1], bytes)), None
        )
        if raw_message is None:
            raise ReceiptImportError("El mensaje IMAP no contiene datos RFC822")
        message = message_from_bytes(raw_message)
        message_id = message.get("Message-ID") or f"imap:{message_number.decode(errors='replace')}"
        imported = 0
        for index, (filename, pdf_bytes) in enumerate(self._pdf_attachments(message)):
            result = self.import_pdf(pdf_bytes, filename, message_id, index)
            imported += int(result.imported)
        return imported

    @staticmethod
    def _pdf_attachments(message: Message) -> list[tuple[str | None, bytes]]:
        attachments: list[tuple[str | None, bytes]] = []
        for part in message.walk():
            if part.is_multipart():
                continue
            filename = part.get_filename()
            content_type = part.get_content_type().lower()
            content = part.get_payload(decode=True)
            is_pdf_name = bool(filename and filename.lower().endswith(".pdf"))
            if content and (content_type == "application/pdf" or is_pdf_name):
                attachments.append((filename, content))
        return attachments

    def _save_pdf(self, content: bytes, file_hash: str) -> Path:
        target = self.settings.app_data_dir / "receipts" / f"{file_hash}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content)
        return target

    @staticmethod
    def _display_filename(filename: str | None) -> str:
        if not filename:
            return "receipt.pdf"
        return Path(filename).name.replace("\x00", "")[:512] or "receipt.pdf"

    def _find_semantic_duplicate(
        self,
        session: Session,
        parsed: ParsedReceipt,
    ) -> Receipt | None:
        """Find the same purchase even when a new OCR pass changes the PDF bytes."""
        candidates = session.scalars(
            select(Receipt)
            .join(Receipt.store)
            .options(selectinload(Receipt.items))
            .where(
                Store.slug == "mercadona",
                Receipt.purchased_at == parsed.purchased_at,
                Receipt.total == parsed.total,
            )
        ).all()
        parsed_signature = self._parsed_item_signature(parsed.items)
        return next(
            (
                receipt
                for receipt in candidates
                if self._stored_item_signature(receipt.items) == parsed_signature
            ),
            None,
        )

    @staticmethod
    def _parsed_item_signature(items: list[ParsedReceiptItem]) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            sorted(
                (
                    item.raw_name.casefold().strip(),
                    str(item.quantity) if item.quantity is not None else "",
                    str(item.total_price) if item.total_price is not None else "",
                )
                for item in items
            )
        )

    @staticmethod
    def _stored_item_signature(items: list[ReceiptItem]) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            sorted(
                (
                    item.raw_name.casefold().strip(),
                    str(item.quantity) if item.quantity is not None else "",
                    str(item.total_price) if item.total_price is not None else "",
                )
                for item in items
            )
        )

    @staticmethod
    def _get_or_create_store(session: Session) -> Store:
        store = session.scalar(select(Store).where(Store.slug == "mercadona"))
        if store is None:
            store = Store(name="Mercadona", slug="mercadona")
            session.add(store)
            session.flush()
        return store

    @staticmethod
    def _get_or_create_product(session: Session, store: Store, raw_name: str) -> Product:
        alias = session.scalar(
            select(ProductAlias).where(
                ProductAlias.store_id == store.id, ProductAlias.raw_name == raw_name
            )
        )
        if alias:
            return alias.product
        product = session.scalar(select(Product).where(Product.name == raw_name))
        if product is None:
            product = Product(name=raw_name)
            session.add(product)
            session.flush()
        session.add(ProductAlias(store=store, raw_name=raw_name, product=product))
        session.flush()
        return product

    def _append_item(
        self,
        session: Session,
        receipt: Receipt,
        store: Store,
        item: ParsedReceiptItem,
    ) -> None:
        product = self._get_or_create_product(session, store, item.raw_name)
        receipt.items.append(
            ReceiptItem(
                product=product,
                raw_name=item.raw_name,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                price_per_kg=item.price_per_kg,
                total_price=item.total_price,
                raw_text=item.raw_text,
            )
        )

    @staticmethod
    def _append_vat_breakdown(receipt: Receipt, vat_breakdown: list[ParsedReceiptVat]) -> None:
        for vat in vat_breakdown:
            receipt.vat_breakdown.append(
                ReceiptVat(
                    rate=vat.rate,
                    taxable_base=vat.taxable_base,
                    tax_amount=vat.tax_amount,
                    raw_text=vat.raw_text,
                )
            )

    def _duplicate_result(self, session: Session, receipt: Receipt) -> ImportResult:
        if receipt.items or not receipt.source_extracted_text:
            return ImportResult(receipt.id, imported=False, duplicate=True, warnings=[])

        try:
            parsed = self.parser.parse(receipt.source_extracted_text)
        except ValueError as exc:
            logger.warning("Could not repair incomplete duplicate receipt %s: %s", receipt.id, exc)
            return ImportResult(
                receipt.id,
                imported=False,
                duplicate=True,
                warnings=[str(exc)],
            )

        self._replace_normalized_data(session, receipt, parsed)
        session.commit()
        return ImportResult(
            receipt.id,
            imported=False,
            duplicate=True,
            warnings=parsed.warnings
        )

    def _replace_normalized_data(
        self,
        session: Session,
        receipt: Receipt,
        parsed: ParsedReceipt,
    ) -> None:
        receipt.purchased_at = parsed.purchased_at
        receipt.total = parsed.total
        receipt.parser_warnings = json.dumps(parsed.warnings, ensure_ascii=False)
        receipt.items.clear()
        receipt.vat_breakdown.clear()
        session.flush()
        store = receipt.store
        for item in parsed.items:
            self._append_item(session, receipt, store, item)
        self._append_vat_breakdown(receipt, parsed.vat_breakdown)

    def _set_status(self, **values: object) -> None:
        with self._status_lock:
            for key, value in values.items():
                setattr(self._status, key, value)
