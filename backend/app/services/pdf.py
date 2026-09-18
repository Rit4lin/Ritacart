from __future__ import annotations

import re
import unicodedata

import fitz


MAX_RECEIPT_PDF_BYTES = 20 * 1024 * 1024
MAX_RECEIPT_PAGES = 20


class PdfExtractionError(ValueError):
    """Raised when an uploaded attachment is not a readable text PDF."""


def _normalise_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("\u00a0", " ")
        .replace("\u00ad", "")
        .replace("\u200b", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    text = re.sub(r"(?<=\d)\s*([,./-])\s*(?=\d)", r"\1", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def extract_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        raise PdfExtractionError("El archivo está vacío")
    if len(pdf_bytes) > MAX_RECEIPT_PDF_BYTES:
        raise PdfExtractionError("El PDF supera el límite de 20 MB")
    if b"%PDF-" not in pdf_bytes[:1024]:
        raise PdfExtractionError("El archivo no parece ser un PDF")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise PdfExtractionError("El PDF está protegido con contraseña")
            if document.page_count == 0:
                raise PdfExtractionError("El PDF no contiene páginas")
            if document.page_count > MAX_RECEIPT_PAGES:
                raise PdfExtractionError("El PDF tiene demasiadas páginas para ser un ticket")

            text = _normalise_text(
                "\n".join(page.get_text("text", sort=True) for page in document)
            )
    except PdfExtractionError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise PdfExtractionError("No se ha podido leer el PDF") from exc

    if not text:
        raise PdfExtractionError(
            "El PDF no contiene texto extraíble. Aplica OCR en Adobe Acrobat y guarda el archivo antes de importarlo."
        )
    return text
