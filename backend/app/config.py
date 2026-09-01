from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_data_dir: Path
    database_url: str
    timezone: str
    email_host: str
    email_port: int
    email_use_ssl: bool
    email_username: str
    email_password: str
    email_folder: str
    email_receipt_sender: str
    email_poll_interval_minutes: int

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_username and self.email_password)


def get_settings() -> Settings:
    """Load the small set of configuration values needed by this phase."""
    default_data_dir = Path(__file__).resolve().parents[2] / "data"
    data_dir = Path(os.getenv("APP_DATA_DIR", str(default_data_dir)))
    database_url = os.getenv(
        "DATABASE_URL", f"sqlite:///{data_dir.as_posix()}/ritacart.db"
    )
    return Settings(
        app_data_dir=data_dir,
        database_url=database_url,
        timezone=os.getenv("APP_TIMEZONE", "Europe/Madrid"),
        email_host=os.getenv("EMAIL_HOST", "imap.gmail.com"),
        email_port=int(os.getenv("EMAIL_PORT", "993")),
        email_use_ssl=os.getenv("EMAIL_USE_SSL", "true").lower() in {"1", "true", "yes"},
        email_username=os.getenv("EMAIL_USERNAME", ""),
        email_password=os.getenv("EMAIL_PASSWORD", ""),
        email_folder=os.getenv("EMAIL_FOLDER", "INBOX"),
        email_receipt_sender=os.getenv(
            "EMAIL_RECEIPT_SENDER", "ticket_digital@mail.mercadona.com"
        ),
        email_poll_interval_minutes=max(
            1, int(os.getenv("EMAIL_POLL_INTERVAL_MINUTES", "15"))
        ),
    )
