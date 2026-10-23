from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings


INITIAL_CATEGORIES = (
    ("Carne", "carne"), ("Pescado", "pescado"), ("Fruta", "fruta"),
    ("Verdura", "verdura"), ("Lácteos", "lacteos"), ("Pan y cereales", "pan-cereales"),
    ("Bebidas", "bebidas"), ("Congelados", "congelados"), ("Despensa", "despensa"),
    ("Limpieza", "limpieza"), ("Higiene", "higiene"), ("Bebé", "bebe"), ("Otros", "otros"),
)


class Base(DeclarativeBase):
    """Base class for future receipt and product models."""


def create_database_engine(settings: Settings) -> Engine:
    """Create the SQLite engine used by the local-first application."""
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)

    if settings.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite_connection(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.close()

    return engine


def initialise_database(engine: Engine) -> None:
    """Create the schema, apply additive SQLite upgrades, and seed stable categories."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "receipts" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("receipts")}
        if "source_extracted_text" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE receipts ADD COLUMN source_extracted_text TEXT NOT NULL DEFAULT ''")
                )
    if "receipts" in inspector.get_table_names():
        receipt_columns = {column["name"] for column in inspector.get_columns("receipts")}
        with engine.begin() as connection:
            if "subtotal" not in receipt_columns:
                connection.execute(text("ALTER TABLE receipts ADD COLUMN subtotal NUMERIC(12, 2)"))
            if "reference" not in receipt_columns:
                connection.execute(text("ALTER TABLE receipts ADD COLUMN reference VARCHAR(120)"))
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_receipt_store_reference "
                "ON receipts (store_id, reference)"
            ))
    if "receipt_items" in inspector.get_table_names():
        item_columns = {column["name"] for column in inspector.get_columns("receipt_items")}
        with engine.begin() as connection:
            if "gross_total_price" not in item_columns:
                connection.execute(text("ALTER TABLE receipt_items ADD COLUMN gross_total_price NUMERIC(12, 2)"))
            if "discount_amount" not in item_columns:
                connection.execute(text(
                    "ALTER TABLE receipt_items ADD COLUMN discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0"
                ))
    if "products" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("products")}
        if "category_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE products ADD COLUMN category_id INTEGER REFERENCES categories(id)"))
    with engine.begin() as connection:
        for sort_order, (name, slug) in enumerate(INITIAL_CATEGORIES, start=1):
            connection.execute(
                text("INSERT OR IGNORE INTO categories (name, slug, sort_order, created_at) VALUES (:name, :slug, :sort_order, CURRENT_TIMESTAMP)"),
                {"name": name, "slug": slug, "sort_order": sort_order},
            )

def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
