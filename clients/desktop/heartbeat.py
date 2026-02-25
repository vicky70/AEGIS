"""AEGIS Desktop Monitor — Heartbeat sender.

Posts a heartbeat to the server every *heartbeat.interval_seconds*.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone

import requests
import sys
import yaml

logger = logging.getLogger("aegis.heartbeat")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class HeartbeatClient:
    """Sends periodic heartbeat POSTs to the AEGIS server."""

    def __init__(self) -> None:
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._component_id: str = cfg["component"]["id"]
        self._interval: int = cfg["heartbeat"]["interval_seconds"]

        self._sequence: int = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # -- public API --------------------------------------------------------

    def start(self) -> None:
        self._stop_event.clear()
        self._sequence = 0
        self._thread = threading.Thread(
            target=self._run, name="HeartbeatClient", daemon=True
        )
        self._thread.start()
        logger.info("HeartbeatClient started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("HeartbeatClient stopped")

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- loop --------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._send()
            self._stop_event.wait(self._interval)

    def _send(self) -> None:
        payload = {
            "component_id": self._component_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_number": self._sequence,
            "status": "running",
        }
        try:
            resp = requests.post(
                f"{self._base_url}/api/v1/system/heartbeat",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            self._sequence += 1
        except Exception as exc:
            logger.warning("Heartbeat POST failed: %s", exc)
