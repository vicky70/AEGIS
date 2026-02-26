"""AEGIS Desktop Monitor — Orchestrator.

Spawns and monitors all worker threads: ActivityTracker, HeartbeatClient,
LogUploader, and EventListener.
"""

from __future__ import annotations

import logging
import os
import platform
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests
import sys
import yaml

from activity_tracker import ActivityTracker
from heartbeat import HeartbeatClient
from uploader import LogUploader
from event_listener import EventListener

logger = logging.getLogger("aegis.orchestrator")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

_HEALTH_CHECK_INTERVAL = 10  # seconds


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class Orchestrator:
    """Manages the lifecycle of all desktop monitor components."""

    def __init__(self) -> None:
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._component_id: str = cfg["component"]["id"]

        # Instantiate components
        self._tracker = ActivityTracker()
        self._uploader = LogUploader()
        self._heartbeat = HeartbeatClient()
        self._event_listener = EventListener()

        self._stop_event = threading.Event()
        self._health_thread: threading.Thread | None = None

        # Component registry for health checks
        self._components: dict[str, Any] = {}

    # -- public API --------------------------------------------------------

    def start_all(self) -> None:
        """Start all components in dependency order, then the health monitor."""
        # 0. Ensure this client is registered with the server
        self._ensure_registered()

        # 1. Tracker first (uploader depends on it)
        self._tracker.start()
        self._components["ActivityTracker"] = self._tracker

        # 2. Uploader (needs tracker reference)
        self._uploader.start(self._tracker)
        self._components["LogUploader"] = self._uploader

        # 3. Heartbeat
        self._heartbeat.start()
        self._components["HeartbeatClient"] = self._heartbeat

        # 4. Event listener
        self._event_listener.start()
        self._components["EventListener"] = self._event_listener

        # Start health-check loop
        self._stop_event.clear()
        self._health_thread = threading.Thread(
            target=self._health_loop, name="HealthMonitor", daemon=True
        )
        self._health_thread.start()

        logger.info("Orchestrator: all components started")

    def stop_all(self) -> None:
        """Stop all components in reverse order."""
        self._stop_event.set()

        # Reverse order
        self._event_listener.stop()
        self._heartbeat.stop()
        self._uploader.stop()
        self._tracker.stop()

        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5)

        logger.info("Orchestrator: all components stopped")

    # -- registration ------------------------------------------------------

    def _ensure_registered(self) -> None:
        """Check if this component is registered with the server; register if not."""
        url = f"{self._base_url}/api/v1/system/components/{self._component_id}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                logger.info("Component '%s' already registered", self._component_id)
                return
        except requests.ConnectionError:
            logger.warning(
                "Server unreachable at %s — skipping registration check", self._base_url
            )
            return
        except Exception as exc:
            logger.warning("Registration check failed: %s", exc)
            return

        # Component not found (404) — register it
        logger.info("Component '%s' not found — registering now", self._component_id)
        register_url = f"{self._base_url}/api/v1/system/components/register"
        payload = {
            "component_id": self._component_id,
            "component_type": "desktop_client",
            "device_id": platform.node(),
            "public_key": "",
            "expected_hash": "",
        }
        try:
            resp = requests.post(register_url, json=payload, timeout=10)
            if resp.status_code == 201:
                logger.info("Component '%s' registered successfully", self._component_id)
            else:
                logger.error(
                    "Registration returned %d: %s", resp.status_code, resp.text
                )
        except Exception as exc:
            logger.error("Registration request failed: %s", exc)

    # -- health monitoring -------------------------------------------------

    def _health_loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(_HEALTH_CHECK_INTERVAL)
            if self._stop_event.is_set():
                break
            for name, component in self._components.items():
                if not component.is_alive():
                    logger.warning("Thread %s is dead — attempting restart", name)
                    self._report_thread_death(name)
                    self._attempt_restart(name, component)

    def _report_thread_death(self, thread_name: str) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "thread_died",
            "event_id": 0,
            "severity": "warning",
            "service_state": None,
            "maintenance_window_id": None,
            "classified_as": None,
            "raw_event": {
                "source": "Orchestrator",
                "log": "internal",
                "message": f"Thread {thread_name} died unexpectedly",
                "record_number": 0,
                "computer_name": "",
            },
            "component_id": self._component_id,
        }
        try:
            requests.post(
                f"{self._base_url}/api/v1/tamper-events",
                json=payload,
                timeout=5,
            )
        except Exception as exc:
            logger.warning("Failed to report thread death: %s", exc)

    def _attempt_restart(self, name: str, component: Any) -> None:
        try:
            if name == "LogUploader":
                component.start(self._tracker)
            else:
                component.start()
            # Give it a moment to spin up
            time.sleep(5)
            if component.is_alive():
                logger.info("Successfully restarted %s", name)
                return
        except Exception as exc:
            logger.error("Restart of %s failed: %s", name, exc)

        # Restart failed — report critical
        logger.critical("Thread %s could not be restarted", name)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "thread_died",
            "event_id": 0,
            "severity": "critical",
            "service_state": None,
            "maintenance_window_id": None,
            "classified_as": None,
            "raw_event": {
                "source": "Orchestrator",
                "log": "internal",
                "message": f"Thread {name} restart failed — giving up",
                "record_number": 0,
                "computer_name": "",
            },
            "component_id": self._component_id,
        }
        try:
            requests.post(
                f"{self._base_url}/api/v1/tamper-events",
                json=payload,
                timeout=5,
            )
        except Exception:
            pass
        # Stop monitoring this component
        del self._components[name]
