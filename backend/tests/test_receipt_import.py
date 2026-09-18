import fitz

from app.models import Receipt

from conftest import COLUMN_LAYOUT_RECEIPT_TEXT, make_pdf


def test_manual_pdf_import_and_receipt_detail(client, receipt_pdf) -> None:
    response = client.post(
        "/api/receipts/import",
        files={"file": ("mercadona.pdf", receipt_pdf, "application/pdf")},
    )

    assert response.status_code == 201
    receipt_id = response.json()["receipt_id"]
    assert response.json()["imported"] is True

    receipts = client.get("/api/receipts").json()
    assert len(receipts) == 1
    assert receipts[0]["total"] == "3.25"
    assert receipts[0]["source"] == "manual"
    assert receipts[0]["needs_review"] is False
    detail = client.get(f"/api/receipts/{receipt_id}")
    assert detail.status_code == 200
    assert detail.json()["needs_review"] is False
    assert detail.json()["parser_warnings"] == []
    assert "MERCADONA" in detail.json()["source_extracted_text"]
    assert [item["raw_name"] for item in detail.json()["items"]] == [
        "LIMÓN ZERO 2L",
        "PERA CONFERENCIA",
    ]


def test_pdf_hash_duplicate_is_idempotent(client, receipt_pdf) -> None:
    files = {"file": ("ticket.pdf", receipt_pdf, "application/pdf")}
    first = client.post("/api/receipts/import", files=files)
    second = client.post("/api/receipts/import", files=files)

    assert first.json()["imported"] is True
    assert second.json()["duplicate"] is True
    assert len(client.get("/api/receipts").json()) == 1


def test_message_id_duplicate_is_idempotent(client, receipt_pdf) -> None:
    importer = client.app.state.importer
    first = importer.import_pdf(receipt_pdf, "one.pdf", "<mail-1@example.test>", 0)
    second = importer.import_pdf(
        make_pdf("01/08/2026 15:00\n1 AGUA 0,50 0,50\nTOTAL 0,50"),
        "two.pdf",
        "<mail-1@example.test>",
        0,
    )

    assert first.imported is True
    assert second.duplicate is True
    assert len(client.get("/api/receipts").json()) == 1


def test_duplicate_incomplete_receipt_is_automatically_reprocessed(client) -> None:
    pdf = make_pdf(COLUMN_LAYOUT_RECEIPT_TEXT)
    first = client.post(
        "/api/receipts/import",
        files={"file": ("mercadona.pdf", pdf, "application/pdf")},
    )
    receipt_id = first.json()["receipt_id"]

    with client.app.state.session_factory() as session:
        receipt = session.get(Receipt, receipt_id)
        assert receipt is not None
        receipt.items.clear()
        receipt.parser_warnings = '["No se ha podido interpretar ninguna línea de producto"]'
        session.commit()

    incomplete = client.get(f"/api/receipts/{receipt_id}").json()
    assert incomplete["needs_review"] is True
    assert incomplete["parser_warnings"] == ["No se ha podido interpretar ninguna línea de producto"]

    second = client.post(
        "/api/receipts/import",
        files={"file": ("mercadona.pdf", pdf, "application/pdf")},
    )

    assert second.status_code == 201
    assert second.json()["duplicate"] is True
    detail = client.get(f"/api/receipts/{receipt_id}").json()
    assert detail["item_count"] == 4
    assert [item["raw_name"] for item in detail["items"]] == [
        "BEBIDA VEGETAL",
        "REFRESCO SIN AZÚCAR",
        "QUESO FRESCO",
        "PERA DE TEMPORADA",
    ]


def test_reprocess_receipt_replaces_bad_normalized_data(client) -> None:
    pdf = make_pdf(COLUMN_LAYOUT_RECEIPT_TEXT)
    imported = client.post(
        "/api/receipts/import",
        files={"file": ("mercadona.pdf", pdf, "application/pdf")},
    )
    receipt_id = imported.json()["receipt_id"]
    with client.app.state.session_factory() as session:
        receipt = session.get(Receipt, receipt_id)
        assert receipt is not None
        receipt.total = "11.10"
        receipt.items.clear()
        receipt.source_extracted_text = "texto corrupto"
        session.commit()

    response = client.post(f"/api/receipts/{receipt_id}/reprocess")

    assert response.status_code == 200
    detail = client.get(f"/api/receipts/{receipt_id}").json()
    assert detail["total"] == "12.46"
    assert detail["item_count"] == 4
    assert detail["vat_breakdown"] == [
        {"rate": "4.00", "taxable_base": "2.50", "tax_amount": "0.10"},
        {"rate": "10.00", "taxable_base": "5.00", "tax_amount": "0.50"},
        {"rate": "21.00", "taxable_base": "3.60", "tax_amount": "0.76"},
    ]


def test_manual_ocr_pdf_with_spaced_punctuation_is_imported(client) -> None:
    pdf = make_pdf(
        """MERCADONA
01 . 08 . 2026 14:30
Descripcion
P. Unit.
Importe
1 PAN DE MOLDE 1 , 25
2 AGUA MINERAL 0 , 55 1 , 10
TOTAL 2 , 35
"""
    )

    response = client.post(
        "/api/receipts/import",
        files={"file": ("ticket-escaneado-ocr.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 201
    detail = client.get(f"/api/receipts/{response.json()['receipt_id']}").json()
    assert detail["total"] == "2.35"
    assert [item["raw_name"] for item in detail["items"]] == ["PAN DE MOLDE", "AGUA MINERAL"]
    assert detail["needs_review"] is False


def test_textless_scan_explains_that_ocr_is_required(client) -> None:
    document = fitz.open()
    document.new_page()
    pdf = document.tobytes()
    document.close()

    response = client.post(
        "/api/receipts/import",
        files={"file": ("scan-sin-ocr.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]
