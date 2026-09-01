from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_settings
from .database import create_database_engine, get_session_factory, initialise_database
from . import models  # noqa: F401 - registers SQLAlchemy metadata before create_all
from .services.importer import ReceiptImportService
from .services.poller import EmailPoller


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.app_data_dir / "receipts").mkdir(exist_ok=True)

    engine = create_database_engine(settings)
    initialise_database(engine)
    session_factory = get_session_factory(engine)
    importer = ReceiptImportService(settings, session_factory)
    poller = EmailPoller(importer, settings.email_poll_interval_minutes)
    app.state.settings = settings
    app.state.database_engine = engine
    app.state.session_factory = session_factory
    app.state.importer = importer
    app.state.poller = poller
    poller.start()
    yield
    poller.stop()
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="RitaCart", version="0.1.0", lifespan=lifespan)

    app.include_router(router)

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
