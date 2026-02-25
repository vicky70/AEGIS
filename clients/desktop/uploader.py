"""AEGIS Desktop Monitor — Batch activity-log uploader.

Drains completed session documents from the ActivityTracker every
*uploader.batch_interval_seconds* and POSTs them to the server.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import TYPE_CHECKING

import requests
import yaml

if TYPE_CHECKING:
    from activity_tracker import ActivityTracker

logger = logging.getLogger("aegis.uploader")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class LogUploader:
    """Periodically drains the tracker queue and uploads to the server."""

    def __init__(self) -> None:
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._interval: int = cfg["uploader"]["batch_interval_seconds"]

        self._tracker: ActivityTracker | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # -- public API --------------------------------------------------------

    def start(self, tracker: ActivityTracker) -> None:
        self._tracker = tracker
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="LogUploader", daemon=True
        )
        self._thread.start()
        logger.info("LogUploader started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        # Flush one final time before stopping
        if self._tracker:
            self._upload()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)
        logger.info("LogUploader stopped")

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- loop --------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._upload()
            self._stop_event.wait(self._interval)

    def _upload(self) -> None:
        if not self._tracker:
            return
        sessions = self._tracker.get_completed_sessions()
        if not sessions:
            return
        try:
            resp = requests.post(
                f"{self._base_url}/api/v1/activity-logs/batch",
                json=sessions,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Uploaded %d session(s) to server", len(sessions))
        except Exception as exc:
            logger.warning("Activity log upload failed (%d sessions): %s", len(sessions), exc)
