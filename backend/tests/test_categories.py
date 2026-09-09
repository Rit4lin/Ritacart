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


def test_database_upgrade_from_pre_categories_schema_preserves_all_receipt_evidence(tmp_path) -> None:
    """Exercise the exact startup upgrade against a representative pre-Fase 3 SQLite file."""
    path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE stores (id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, slug VARCHAR(80) NOT NULL UNIQUE)",
            "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE, created_at DATETIME NOT NULL)",
            "CREATE TABLE product_aliases (id INTEGER PRIMARY KEY, store_id INTEGER NOT NULL, raw_name VARCHAR(255) NOT NULL, product_id INTEGER NOT NULL, UNIQUE(store_id, raw_name))",
            "CREATE TABLE receipts (id INTEGER PRIMARY KEY, store_id INTEGER NOT NULL, purchased_at DATETIME NOT NULL, total NUMERIC(12, 2) NOT NULL, source_message_id VARCHAR(512), source_attachment_index INTEGER, source_filename VARCHAR(512) NOT NULL, source_file_hash VARCHAR(64) NOT NULL UNIQUE, source_pdf_path VARCHAR(1024) NOT NULL, source_extracted_text TEXT NOT NULL, parser_warnings TEXT, imported_at DATETIME NOT NULL, UNIQUE(source_message_id, source_attachment_index))",
            "CREATE TABLE receipt_items (id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL, product_id INTEGER, raw_name VARCHAR(255) NOT NULL, quantity NUMERIC(12, 3), unit VARCHAR(24), unit_price NUMERIC(12, 4), price_per_kg NUMERIC(12, 4), total_price NUMERIC(12, 2), raw_text TEXT NOT NULL)",
            "CREATE TABLE receipt_vat (id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL, rate NUMERIC(5, 2) NOT NULL, taxable_base NUMERIC(12, 2) NOT NULL, tax_amount NUMERIC(12, 2) NOT NULL, raw_text TEXT NOT NULL, UNIQUE(receipt_id, rate))",
        ):
            connection.execute(text(statement))
        connection.execute(text("INSERT INTO stores (id, name, slug) VALUES (1, 'Mercadona', 'mercadona')"))
        connection.execute(text("INSERT INTO products (id, name, created_at) VALUES (1, 'ARROZ', CURRENT_TIMESTAMP), (2, 'LECHE', CURRENT_TIMESTAMP), (3, 'POLLO', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO product_aliases (id, store_id, raw_name, product_id) VALUES (1, 1, 'ARROZ REDONDO', 1), (2, 1, 'LECHE ENTERA', 2), (3, 1, 'POLLO FRESCO', 3)"))
        connection.execute(text("INSERT INTO receipts (id, store_id, purchased_at, total, source_message_id, source_attachment_index, source_filename, source_file_hash, source_pdf_path, source_extracted_text, imported_at) VALUES (1, 1, '2026-01-10 10:00:00', 12.50, 'message-1', 0, 'one.pdf', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '/data/receipts/one.pdf', 'evidence one', CURRENT_TIMESTAMP), (2, 1, '2026-02-10 11:00:00', 9.00, 'message-2', 0, 'two.pdf', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', '/data/receipts/two.pdf', 'evidence two', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO receipt_items (id, receipt_id, product_id, raw_name, quantity, unit, unit_price, total_price, raw_text) VALUES (1, 1, 1, 'ARROZ REDONDO', 2, 'ud', 1.50, 3.00, 'raw rice'), (2, 1, 2, 'LECHE ENTERA', 3, 'ud', 1.20, 3.60, 'raw milk'), (3, 2, 3, 'POLLO FRESCO', 1, 'ud', 5.40, 5.40, 'raw chicken')"))
        connection.execute(text("INSERT INTO receipt_vat (id, receipt_id, rate, taxable_base, tax_amount, raw_text) VALUES (1, 1, 10, 6.00, 0.60, 'vat 10'), (2, 1, 21, 5.00, 1.05, 'vat 21'), (3, 2, 10, 8.18, 0.82, 'vat 10 second')"))
        before = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("stores", "products", "product_aliases", "receipts", "receipt_items", "receipt_vat")
        }
    initialise_database(engine)
    with engine.connect() as connection:
        assert "category_id" in {column["name"] for column in inspect(engine).get_columns("products")}
        after_first = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in before
        }
        assert after_first == before == {"stores": 1, "products": 3, "product_aliases": 3, "receipts": 2, "receipt_items": 3, "receipt_vat": 3}
        assert connection.execute(text("SELECT COUNT(*) FROM products WHERE category_id IS NULL")).scalar_one() == 3
        assert connection.execute(text("SELECT COUNT(*) FROM categories")).scalar_one() == 13
    initialise_database(engine)
    with engine.connect() as connection:
        after_second = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in before
        }
        assert after_second == after_first
        assert connection.execute(text("SELECT COUNT(*) FROM categories")).scalar_one() == 13
        assert connection.execute(text("SELECT COUNT(*) FROM products WHERE category_id IS NULL")).scalar_one() == 3
