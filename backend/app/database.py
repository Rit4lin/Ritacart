from __future__ import annotations

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings


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
    """Create the schema and apply the one additive compatibility change so far."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "receipts" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("receipts")}
        if "source_extracted_text" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE receipts ADD COLUMN source_extracted_text TEXT NOT NULL DEFAULT ''")
                )

def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
