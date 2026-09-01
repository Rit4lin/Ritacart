from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_data_dir: Path
    database_url: str
    timezone: str


def get_settings() -> Settings:
    """Load the small set of configuration values needed by this phase."""
    data_dir = Path(os.getenv("APP_DATA_DIR", "/data"))
    database_url = os.getenv(
        "DATABASE_URL", f"sqlite:///{data_dir.as_posix()}/ritacart.db"
    )
    return Settings(
        app_data_dir=data_dir,
        database_url=database_url,
        timezone=os.getenv("APP_TIMEZONE", "Europe/Madrid"),
    )
