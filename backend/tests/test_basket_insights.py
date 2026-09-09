from __future__ import annotations

from datetime import datetime

from app.analytics.basket import basket_insights
from conftest import make_pdf


def _import_receipt(client, date: str, lines: str, total: str) -> None:
    response = client.post(
        "/api/receipts/import",
        files={"file": (f"{date}-{total}.pdf", make_pdf(f"MERCADONA\n{date} 10:00\n{lines}\nTOTAL {total}\n"), "application/pdf")},
    )
    assert response.status_code == 201


def test_basket_recurrence_due_states_and_personal_inflation(client) -> None:
    _import_receipt(client, "01/01/2026", "1 HUEVOS 2,00 2,00\n1 IRREGULAR 1,00 1,00", "3,00")
    _import_receipt(client, "02/01/2026", "1 IRREGULAR 1,00 1,00", "1,00")
    _import_receipt(client, "11/01/2026", "1 HUEVOS 3,00 3,00", "3,00")
    _import_receipt(client, "21/01/2026", "1 HUEVOS 4,00 4,00", "4,00")
    _import_receipt(client, "10/02/2026", "1 HUEVOS 5,00 5,00\n1 IRREGULAR 1,00 1,00", "6,00")
    _import_receipt(client, "15/02/2026", "1 NUEVO 5,00 5,00", "5,00")
    with client.app.state.session_factory() as session:
        data = basket_insights(session, datetime(2026, 2, 20, 12, 0))

    basket = data["basket"]
    assert [item["name"] for item in basket["items"]] == ["HUEVOS"]
    assert basket["items"][0]["average_days_between_purchases"] == "13.3"
    assert basket["items"][0]["median_days_between_purchases"] == "10.0"
    assert basket["items"][0]["days_since_last_purchase"] == 10
    assert basket["current_basket_cost"] == "5.00"
    assert data["due_soon_products"][0]["name"] == "HUEVOS"
    assert data["due_soon_products"][0]["status"] == "toca"
    assert not data["inactive_regular_products"]
    assert data["new_products"][0]["name"] == "NUEVO"
    assert data["most_regular_products"][0]["name"] == "HUEVOS"
    assert basket["basket_price_history"][0] == {"month": "2026-01", "cost": "4.00", "coverage": "1.00"}
    # The January point only knows the final January price; the February price cannot leak backwards.
    assert basket["personal_inflation"] == {"baseline_month": "2026-01", "baseline_cost": "4.00", "current_cost": "5.00", "change_absolute": "1.00", "change_percent": "25.0", "coverage_current": "1.00", "coverage_baseline": "1.00"}
    assert all(item["name"] != "IRREGULAR" for item in data["most_regular_products"])


def test_basket_handles_empty_and_inactive_regular_products(client) -> None:
    with client.app.state.session_factory() as session:
        empty = basket_insights(session, datetime(2026, 5, 1, 12, 0))
    assert empty["basket"]["items"] == []
    assert empty["basket"]["personal_inflation"] is None

    _import_receipt(client, "01/01/2026", "1 YOGUR 1,00 1,00", "1,00")
    _import_receipt(client, "11/01/2026", "1 YOGUR 1,00 1,00", "1,00")
    _import_receipt(client, "21/01/2026", "1 YOGUR 1,00 1,00", "1,00")
    with client.app.state.session_factory() as session:
        data = basket_insights(session, datetime(2026, 2, 20, 12, 0))
    assert data["inactive_regular_products"][0]["name"] == "YOGUR"
    assert data["basket"]["items"] == []
