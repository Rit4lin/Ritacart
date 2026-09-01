from conftest import make_pdf


def _import_receipt(client, text: str) -> None:
    response = client.post(
        "/api/receipts/import",
        files={"file": ("mercadona.pdf", make_pdf(text), "application/pdf")},
    )
    assert response.status_code == 201


def test_product_analytics_top_products_and_manual_merge(client) -> None:
    _import_receipt(
        client,
        """MERCADONA
10/01/2026 10:00
1 POLLO DESHUESA 4,50 4,50
1 POLLO DESHUESA 4,80 4,80
1 AGUA 0,50 0,50
TOTAL 9,80
""",
    )
    _import_receipt(
        client,
        """MERCADONA
10/02/2026 10:00
1 POLLO DESHUESA 5,00 5,00
2 AGUA 0,50 1,00
TOTAL 6,00
""",
    )
    _import_receipt(
        client,
        """MERCADONA
11/03/2026 10:00
1 POLLO DESHUESADO 5,20 5,20
TOTAL 5,20
""",
    )

    products = client.get("/api/products").json()
    product_ids = {product["name"]: product["id"] for product in products}
    merged = client.post(
        f"/api/products/{product_ids['POLLO DESHUESADO']}/merge",
        json={"target_product_id": product_ids["POLLO DESHUESA"]},
    )

    assert merged.status_code == 200
    assert merged.json()["target_name"] == "POLLO DESHUESA"
    analytics = client.get(f"/api/products/{product_ids['POLLO DESHUESA']}/analytics")
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["purchase_count"] == 3
    assert data["total_quantity"] == "4.000"
    assert data["aliases"] == ["POLLO DESHUESA", "POLLO DESHUESADO"]
    assert data["monthly_purchases"] == [
        {"month": "2026-01", "purchase_count": 1, "total_quantity": "2.000"},
        {"month": "2026-02", "purchase_count": 1, "total_quantity": "1.000"},
        {"month": "2026-03", "purchase_count": 1, "total_quantity": "1.000"},
    ]
    assert data["seasonal_purchases"] == [
        {"month": 1, "purchase_count": 1},
        {"month": 2, "purchase_count": 1},
        {"month": 3, "purchase_count": 1},
    ]
    assert data["price_history"] == [
        {"date": "2026-01-10", "price": "4.8000", "price_unit": "€/ud"},
        {"date": "2026-02-10", "price": "5.0000", "price_unit": "€/ud"},
        {"date": "2026-03-11", "price": "5.2000", "price_unit": "€/ud"},
    ]
    assert client.get("/api/analytics/products/top").json() == [
        {
            "id": product_ids["POLLO DESHUESA"],
            "name": "POLLO DESHUESA",
            "purchase_count": 3,
            "total_quantity": "4.000",
            "last_purchased_at": "2026-03-11T10:00:00",
        },
        {
            "id": product_ids["AGUA"],
            "name": "AGUA",
            "purchase_count": 2,
            "total_quantity": "3.000",
            "last_purchased_at": "2026-02-10T10:00:00",
        },
    ]
