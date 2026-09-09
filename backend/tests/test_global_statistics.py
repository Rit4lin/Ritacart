from __future__ import annotations

from datetime import datetime

from conftest import make_pdf


def _import_receipt(client, date: str, total: str, hour: str = "10:00") -> None:
    response = client.post(
        "/api/receipts/import",
        files={
            "file": (
                f"{date}-{hour}.pdf",
                make_pdf(f"MERCADONA\n{date} {hour}\n1 PRODUCTO {total} {total}\nTOTAL {total}\n"),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201


def _fixed_now(monkeypatch) -> None:
    monkeypatch.setattr("app.analytics.statistics._local_now", lambda _: datetime(2026, 12, 15, 12, 0))


def test_statistics_calculates_period_comparisons_and_distributions(client, monkeypatch) -> None:
    _fixed_now(monkeypatch)
    _import_receipt(client, "10/11/2026", "10,00", "09:00")  # Tuesday
    _import_receipt(client, "20/11/2026", "20,00", "20:00")
    _import_receipt(client, "05/12/2026", "30,00", "20:00")
    _import_receipt(client, "05/12/2025", "40,00")

    data = client.get("/api/analytics/statistics?range=3m").json()
    assert data["period"] == {
        "total_spend": "60.00",
        "receipt_count": 3,
        "average_basket": "20.00",
        "average_weekly_spend": "5.56",
        "average_days_between_shops": "12.7",
    }
    assert data["comparisons"]["current_month"] == {
        "current": "30.00", "previous": "30.00", "difference": "0.00", "percentage_change": "0.0"
    }
    assert data["comparisons"]["current_year"] == {
        "current": "60.00", "previous": "40.00", "difference": "20.00", "percentage_change": "50.0"
    }
    assert data["monthly_spend"] == [
        {"month": "2026-10", "total_spend": "0.00", "receipt_count": 0, "average_basket": "0.00"},
        {"month": "2026-11", "total_spend": "30.00", "receipt_count": 2, "average_basket": "15.00"},
        {"month": "2026-12", "total_spend": "30.00", "receipt_count": 1, "average_basket": "30.00"},
    ]
    assert data["purchases_by_weekday"] == [
        {"weekday": 1, "receipt_count": 0}, {"weekday": 2, "receipt_count": 1},
        {"weekday": 3, "receipt_count": 0}, {"weekday": 4, "receipt_count": 0},
        {"weekday": 5, "receipt_count": 1}, {"weekday": 6, "receipt_count": 1},
        {"weekday": 7, "receipt_count": 0},
    ]
    assert data["purchases_by_hour"][9] == {"hour": 9, "receipt_count": 1}
    assert data["purchases_by_hour"][20] == {"hour": 20, "receipt_count": 2}
    assert len(data["purchases_by_hour"]) == 24


def test_statistics_empty_and_zero_previous_period(client, monkeypatch) -> None:
    _fixed_now(monkeypatch)
    empty = client.get("/api/analytics/statistics?range=all").json()
    assert empty["period"]["total_spend"] == "0.00"
    assert empty["period"]["average_days_between_shops"] is None
    assert empty["monthly_spend"] == []
    assert all(point["receipt_count"] == 0 for point in empty["purchases_by_hour"])

    _import_receipt(client, "10/12/2026", "25,00")
    data = client.get("/api/analytics/statistics?range=6m").json()
    assert data["comparisons"]["current_month"]["percentage_change"] is None
    assert data["comparisons"]["current_year"]["percentage_change"] is None
    assert data["period"]["average_days_between_shops"] is None


def test_statistics_ranges_and_validation(client, monkeypatch) -> None:
    _fixed_now(monkeypatch)
    _import_receipt(client, "10/01/2026", "10,00")
    _import_receipt(client, "10/06/2026", "20,00")
    _import_receipt(client, "10/10/2026", "30,00")
    _import_receipt(client, "10/12/2026", "40,00")

    assert client.get("/api/analytics/statistics?range=3m").json()["period"]["receipt_count"] == 2
    assert client.get("/api/analytics/statistics?range=6m").json()["period"]["receipt_count"] == 2
    assert client.get("/api/analytics/statistics?range=1y").json()["period"]["receipt_count"] == 4
    assert client.get("/api/analytics/statistics?range=all").json()["period"]["receipt_count"] == 4
    assert client.get("/api/analytics/statistics?range=nope").status_code == 422
