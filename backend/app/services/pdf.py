from __future__ import annotations

import fitz


class PdfExtractionError(ValueError):
    """Raised when an uploaded attachment is not a readable text PDF."""


def extract_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes.startswith(b"%PDF"):
        raise PdfExtractionError("El archivo no parece ser un PDF")
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            return "\n".join(page.get_text() for page in document)
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise PdfExtractionError("No se ha podido leer el PDF") from exc
