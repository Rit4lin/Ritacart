from __future__ import annotations

import logging
import threading

from .importer import ReceiptImportService

logger = logging.getLogger(__name__)


class EmailPoller:
    """Small in-process IMAP scheduler; no queue or secondary service is needed."""

    def __init__(self, importer: ReceiptImportService, interval_minutes: int) -> None:
        self.importer = importer
        self.interval_seconds = interval_minutes * 60
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.importer.settings.email_enabled:
            logger.info("Email importer is disabled because credentials are not configured")
            return
        self._thread = threading.Thread(target=self._run, name="ritacart-imap", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.importer.run_imap_import()
            except Exception:  # The status endpoint and logs retain the error.
                logger.exception("Scheduled IMAP import failed")
            self._stop_event.wait(self.interval_seconds)
