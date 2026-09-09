from __future__ import annotations

from conftest import make_pdf


def _import_receipt(client, date: str, lines: str, total: str) -> None:
    response = client.post(
        "/api/receipts/import",
        files={"file": (f"{date}-{total}.pdf", make_pdf(f"MERCADONA\n{date} 10:00\n{lines}\nTOTAL {total}\n"), "application/pdf")},
    )
    assert response.status_code == 201


def test_product_price_summary_spend_frequency_and_monthly_spend(client) -> None:
    _import_receipt(client, "10/01/2026", "1 CAFÉ 2,00 2,00\n1 CAFÉ 2,50 2,50", "4,50")
    _import_receipt(client, "20/01/2026", "1 CAFÉ 3,00 3,00", "3,00")
    _import_receipt(client, "10/02/2026", "1 CAFÉ 2,40 2,40", "2,40")
    product_id = next(product["id"] for product in client.get("/api/products").json() if product["name"] == "CAFÉ")

    data = client.get(f"/api/products/{product_id}/analytics").json()
    assert data["total_spend"] == "9.90"
    assert data["first_purchased_at"] == "2026-01-10T10:00:00"
    assert data["last_purchased_at"] == "2026-02-10T10:00:00"
    assert data["average_days_between_purchases"] == "15.5"
    assert data["monthly_spend"] == [
        {"month": "2026-01", "total_spend": "7.50"},
        {"month": "2026-02", "total_spend": "2.40"},
    ]
    assert data["price_summary"] == [{
        "price_unit": "€/ud", "current_price": "2.40", "previous_price": "3.00",
        "change_absolute": "-0.60", "change_percent": "-20.0", "min_price": "2.40",
        "max_price": "3.00", "average_price": "2.63",
    }]
    assert data["price_history"] == [
        {"date": "2026-01-10", "price": "2.5000", "price_unit": "€/ud"},
        {"date": "2026-01-20", "price": "3.0000", "price_unit": "€/ud"},
        {"date": "2026-02-10", "price": "2.4000", "price_unit": "€/ud"},
    ]


def test_product_insights_rankings_and_price_edge_cases(client) -> None:
    _import_receipt(client, "01/01/2026", "1 SUBE 1,00 1,00\n1 BAJA 4,00 4,00\n1 ÚNICO 9,00 9,00", "14,00")
    _import_receipt(client, "01/02/2026", "1 SUBE 1,50 1,50\n1 BAJA 3,00 3,00\n1 CERO 0,00 0,00", "4,50")
    _import_receipt(client, "01/03/2026", "1 CERO 1,00 1,00\n1 SUBE 1,60 1,60", "2,60")

    insights = client.get("/api/analytics/products/insights").json()
    assert insights["most_expensive_by_spend"][0]["name"] == "ÚNICO"
    assert insights["most_frequently_purchased"][0]["name"] == "SUBE"
    assert insights["biggest_price_increases_percent"][0]["name"] == "SUBE"
    assert insights["biggest_price_decreases_percent"][0]["name"] == "BAJA"
    assert insights["biggest_price_increases_absolute"][0]["name"] == "CERO"
    assert insights["biggest_price_increases_absolute"][0]["change_absolute"] == "1.00"
    assert insights["biggest_price_decreases_absolute"][0]["change_absolute"] == "-1.00"
    assert all(entry["name"] != "ÚNICO" for entry in insights["biggest_price_increases_percent"])
    assert all(entry["name"] != "CERO" for entry in insights["biggest_price_increases_percent"])


def test_product_price_units_and_single_observation(client) -> None:
    _import_receipt(client, "01/01/2026", "MEZCLA\n0,500 kg 2,00 €/kg 1,00", "1,00")
    _import_receipt(client, "01/02/2026", "MEZCLA\n0,500 kg 3,00 €/kg 1,50", "1,50")
    _import_receipt(client, "01/03/2026", "1 MEZCLA 4,00 4,00", "4,00")
    product_id = next(product["id"] for product in client.get("/api/products").json() if product["name"] == "MEZCLA")
    summaries = client.get(f"/api/products/{product_id}/analytics").json()["price_summary"]
    assert summaries == [
        {"price_unit": "€/kg", "current_price": "3.00", "previous_price": "2.00", "change_absolute": "1.00", "change_percent": "50.0", "min_price": "2.00", "max_price": "3.00", "average_price": "2.50"},
        {"price_unit": "€/ud", "current_price": "4.00", "previous_price": None, "change_absolute": None, "change_percent": None, "min_price": "4.00", "max_price": "4.00", "average_price": "4.00"},
    ]
