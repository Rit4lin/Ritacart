from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import create_database_engine, initialise_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.app_data_dir / "receipts").mkdir(exist_ok=True)

    engine = create_database_engine(settings)
    initialise_database(engine)
    app.state.settings = settings
    app.state.database_engine = engine
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="RitaCart", version="0.1.0", lifespan=lifespan)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
