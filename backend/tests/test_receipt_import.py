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
    detail = client.get(f"/api/receipts/{receipt_id}")
    assert detail.status_code == 200
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
