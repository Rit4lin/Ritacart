from __future__ import annotations

from datetime import datetime
from sqlalchemy import create_engine, inspect, text

from app.analytics.categories import category_analytics
from app.database import initialise_database
from conftest import make_pdf


def _import_receipt(client, date: str, lines: str, total: str) -> None:
    response = client.post(
        "/api/receipts/import",
        files={"file": (f"{date}-{total}.pdf", make_pdf(f"MERCADONA\n{date} 10:00\n{lines}\nTOTAL {total}\n"), "application/pdf")},
    )
    assert response.status_code == 201


def test_categories_are_seeded_idempotently_and_can_be_assigned(client) -> None:
    categories = client.get("/api/categories").json()
    assert [category["slug"] for category in categories] == [
        "carne", "pescado", "fruta", "verdura", "lacteos", "pan-cereales", "bebidas",
        "congelados", "despensa", "limpieza", "higiene", "bebe", "otros",
    ]
    assert client.get("/api/categories").json() == categories
    _import_receipt(client, "10/01/2026", "1 ARROZ 2,00 2,00", "2,00")
    product = client.get("/api/products").json()[0]
    assert product["category"] is None
    despensa = next(category for category in categories if category["slug"] == "despensa")
    assert client.patch(f"/api/products/{product['id']}/category", json={"category_id": despensa["id"]}).json()["category"]["slug"] == "despensa"
    assert client.get(f"/api/products/{product['id']}/analytics").json()["category"]["slug"] == "despensa"
    assert client.patch(f"/api/products/{product['id']}/category", json={"category_id": None}).json()["category"] is None


def test_category_analytics_and_product_merge_rules(client) -> None:
    _import_receipt(client, "10/10/2026", "1 POLLO 10,00 10,00\n1 PAN 2,00 2,00\n1 SUELTO 3,00 3,00", "15,00")
    _import_receipt(client, "10/11/2026", "1 POLLO 20,00 20,00", "20,00")
    _import_receipt(client, "10/12/2026", "1 PAN 4,00 4,00", "4,00")
    products = {product["name"]: product for product in client.get("/api/products").json()}
    categories = {category["slug"]: category for category in client.get("/api/categories").json()}
    client.patch(f"/api/products/{products['POLLO']['id']}/category", json={"category_id": categories["carne"]["id"]})
    client.patch(f"/api/products/{products['PAN']['id']}/category", json={"category_id": categories["pan-cereales"]["id"]})
    # Endpoint dates use real time; exercise deterministic calculation directly using the app session.
    with client.app.state.session_factory() as session:
        data = category_analytics(session, "3m", datetime(2026, 12, 15, 12, 0))
        ranges = [
            category_analytics(session, selected_range, datetime(2026, 12, 15, 12, 0))["range"]
            for selected_range in ("6m", "1y", "all")
        ]
    carne = next(category for category in data["categories"] if category["slug"] == "carne")
    uncategorized = next(category for category in data["categories"] if category["slug"] == "uncategorized")
    assert carne["total_spend"] == "30.00"
    assert carne["percentage"] == "76.9"
    assert carne["purchase_count"] == 2
    assert carne["current_month_spend"] == "0.00"
    assert carne["previous_month_spend"] == "20.00"
    assert carne["change_percent"] == "-100.0"
    assert uncategorized["total_spend"] == "3.00"
    assert data["summary"] == {"total_products": 3, "categorized_products": 2, "uncategorized_products": 1, "categorized_percentage": "66.7", "observed_spend": "39.00"}
    assert [month["month"] for month in data["monthly_spend"]] == ["2026-10", "2026-11", "2026-12"]
    assert ranges == ["6m", "1y", "all"]


def test_product_merge_transfers_only_a_missing_target_category(client) -> None:
    _import_receipt(client, "10/01/2026", "1 ORIGEN 1,00 1,00\n1 DESTINO 1,00 1,00", "2,00")
    products = {product["name"]: product for product in client.get("/api/products").json()}
    categories = {category["slug"]: category for category in client.get("/api/categories").json()}
    client.patch(f"/api/products/{products['ORIGEN']['id']}/category", json={"category_id": categories["carne"]["id"]})
    merged = client.post(f"/api/products/{products['ORIGEN']['id']}/merge", json={"target_product_id": products["DESTINO"]["id"]})
    assert merged.status_code == 200
    assert client.get(f"/api/products/{products['DESTINO']['id']}/analytics").json()["category"]["slug"] == "carne"

    _import_receipt(client, "10/02/2026", "1 SEGUNDO 1,00 1,00\n1 DESTINO 1,00 1,00", "2,00")
    second = next(product for product in client.get("/api/products").json() if product["name"] == "SEGUNDO")
    client.patch(f"/api/products/{second['id']}/category", json={"category_id": categories["fruta"]["id"]})
    client.patch(f"/api/products/{products['DESTINO']['id']}/category", json={"category_id": categories["despensa"]["id"]})
    assert client.post(f"/api/products/{second['id']}/merge", json={"target_product_id": products["DESTINO"]["id"]}).status_code == 200
    assert client.get(f"/api/products/{products['DESTINO']['id']}/analytics").json()["category"]["slug"] == "despensa"


def test_database_upgrade_adds_category_column_without_losing_legacy_product(tmp_path) -> None:
    path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE, created_at DATETIME NOT NULL)"))
        connection.execute(text("INSERT INTO products (id, name, created_at) VALUES (1, 'LEGACY', CURRENT_TIMESTAMP)"))
        connection.execute(text("CREATE TABLE receipts (id INTEGER PRIMARY KEY, legacy_value TEXT)"))
        connection.execute(text("CREATE TABLE receipt_items (id INTEGER PRIMARY KEY, legacy_value TEXT)"))
        connection.execute(text("INSERT INTO receipts (id, legacy_value) VALUES (1, 'ticket')"))
        connection.execute(text("INSERT INTO receipt_items (id, legacy_value) VALUES (1, 'linea')"))
    initialise_database(engine)
    with engine.connect() as connection:
        assert "category_id" in {column["name"] for column in inspect(engine).get_columns("products")}
        assert connection.execute(text("SELECT name FROM products WHERE id = 1")).scalar_one() == "LEGACY"
        assert connection.execute(text("SELECT legacy_value FROM receipts WHERE id = 1")).scalar_one() == "ticket"
        assert connection.execute(text("SELECT legacy_value FROM receipt_items WHERE id = 1")).scalar_one() == "linea"
        assert connection.execute(text("SELECT COUNT(*) FROM categories")).scalar_one() == 13
