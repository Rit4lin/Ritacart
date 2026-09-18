from __future__ import annotations

from app.models import Receipt

from conftest import make_pdf


def _import_receipt(client) -> int:
    response = client.post("/api/receipts/import", files={"file": ("ticket.pdf", make_pdf("MERCADONA\n10/02/2026 10:00\n1 POLLO 3,00 3,00\nTOTAL 3,00"), "application/pdf")})
    assert response.status_code == 201
    return response.json()["receipt_id"]


def test_search_pdf_exports_health_and_normalized_item_editing(client) -> None:
    receipt_id = _import_receipt(client)
    detail = client.get(f"/api/receipts/{receipt_id}").json()
    product_id = detail["items"][0]["product_id"]
    assert client.get("/api/search?q=%20pollo%20").json()["products"] == [{"id": product_id, "name": "POLLO"}]
    assert client.get("/api/search?q=10%2F02%2F2026").json()["receipts"][0]["id"] == receipt_id
    assert client.get(f"/api/receipts/{receipt_id}/pdf").headers["content-type"].startswith("application/pdf")
    edited = client.patch(f"/api/receipts/{receipt_id}/items/{detail['items'][0]['id']}", json={"quantity": "2", "total_price": "6.00"})
    assert edited.status_code == 200
    assert edited.json()["quantity"] == "2.000"
    assert client.patch(f"/api/receipts/{receipt_id}/items/{detail['items'][0]['id']}", json={"unit_price": "-1"}).status_code == 422
    assert client.get("/api/data-health").json() == {"total_receipts": 1, "total_receipt_items": 1, "total_products": 1, "uncategorized_products": 1, "receipts_needing_review": 0, "receipts_without_items": 0, "possible_duplicate_receipts": 0, "parser_warning_count": 0}
    csv_response = client.get("/api/export/items.csv")
    assert csv_response.status_code == 200
    assert csv_response.content.startswith("\ufeff".encode())
    assert b"raw_description" in csv_response.content


def test_bulk_categories_is_atomic(client) -> None:
    receipt_id = _import_receipt(client)
    product_id = client.get(f"/api/receipts/{receipt_id}").json()["items"][0]["product_id"]
    category_id = client.get("/api/categories").json()[0]["id"]
    assert client.patch("/api/products/categories", json={"product_ids": [product_id, 999], "category_id": category_id}).status_code == 422
    assert client.get("/api/products").json()[0]["category"] is None
    assert client.patch("/api/products/categories", json={"product_ids": [product_id], "category_id": category_id}).json() == {"updated_products": 1}


def test_malformed_stored_parser_warnings_do_not_break_receipt_views(client) -> None:
    receipt_id = _import_receipt(client)
    with client.app.state.session_factory() as session:
        receipt = session.get(Receipt, receipt_id)
        assert receipt is not None
        receipt.parser_warnings = "{broken-json"
        session.commit()

    detail = client.get(f"/api/receipts/{receipt_id}")
    assert detail.status_code == 200
    assert detail.json()["needs_review"] is True
    assert detail.json()["parser_warnings"] == [
        "Avisos del parser almacenados con un formato no válido"
    ]

    health = client.get("/api/data-health")
    assert health.status_code == 200
    assert health.json()["receipts_needing_review"] == 1
    assert health.json()["parser_warning_count"] == 1
