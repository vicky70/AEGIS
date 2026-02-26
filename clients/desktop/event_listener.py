"""AEGIS Desktop Monitor — Windows Event Log listener.

Polls the System and Security event logs every 10 seconds for tamper-related
events (7036, 7034, 7040, 4656) and reports them to the server.
"""

from __future__ import annotations

import logging
import os
import socket
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import requests
import sys
import yaml

try:
    import win32evtlog
    import win32con
except ImportError:
    win32evtlog = win32con = None  # type: ignore[assignment]

logger = logging.getLogger("aegis.event_listener")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
_SERVICE_NAME = "AEGISMonitor"
_POLL_INTERVAL = 10  # seconds


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EVENT_TYPE_MAP: dict[int, dict[str, str]] = {
    7036: {"event_type": "service_state_change", "severity": "info"},
    7034: {"event_type": "crash", "severity": "critical"},
    7040: {"event_type": "startup_type_changed", "severity": "critical"},
    4656: {"event_type": "stop_attempt_denied", "severity": "warning"},
}


def _extract_message(event: Any) -> str:
    """Best-effort message extraction from a win32evtlog event."""
    try:
        strings = event.StringInserts
        if strings:
            return " | ".join(str(s) for s in strings)
    except Exception:
        pass
    return ""


def _extract_username(message: str) -> str:
    """Attempt to extract the username from a Security 4656 event message."""
    # Typical format: ... Account Name: <username> ...
    for line in message.split("|"):
        line = line.strip()
        if "Account Name" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return "unknown"


# ---------------------------------------------------------------------------
# EventListener
# ---------------------------------------------------------------------------

class EventListener:
    """Monitors Windows Event Logs for tamper-related events."""

    def __init__(self) -> None:
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._component_id: str = cfg["component"]["id"]
        self._monitored_ids: set[int] = set(cfg["tamper_detection"]["event_ids_to_monitor"])
        self._computer_name: str = socket.gethostname()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Track last-read record number per log to avoid re-processing
        self._last_record: dict[str, int] = {"System": 0, "Security": 0}

    # -- public API --------------------------------------------------------

    def start(self) -> None:
        self._stop_event.clear()
        # Initialise last-record positions to current latest
        self._init_positions()
        self._thread = threading.Thread(
            target=self._run, name="EventListener", daemon=True
        )
        self._thread.start()
        logger.info("EventListener started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)
        logger.info("EventListener stopped")

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- initialisation ----------------------------------------------------

    def _init_positions(self) -> None:
        """Set last-record to the current end of each log so we only read new events."""
        for log_name in ("System", "Security"):
            try:
                handle = win32evtlog.OpenEventLog(None, log_name)
                total = win32evtlog.GetNumberOfEventLogRecords(handle)
                self._last_record[log_name] = total
                win32evtlog.CloseEventLog(handle)
            except Exception as exc:
                logger.warning("Cannot init position for %s log: %s", log_name, exc)

    # -- main loop ---------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._poll_log("System", {7036, 7034, 7040})
            self._poll_log("Security", {4656})
            self._stop_event.wait(_POLL_INTERVAL)

    def _poll_log(self, log_name: str, event_ids: set[int]) -> None:
        try:
            handle = win32evtlog.OpenEventLog(None, log_name)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            win32evtlog.CloseEventLog(handle)
        except Exception as exc:
            logger.warning("Cannot read %s log: %s", log_name, exc)
            return

        last = self._last_record.get(log_name, 0)
        new_last = last

        for event in events:
            rec_num = event.RecordNumber
            if rec_num <= last:
                continue  # Already processed
            if rec_num > new_last:
                new_last = rec_num

            eid = event.EventID & 0xFFFF  # Mask for actual event ID
            if eid not in event_ids:
                continue

            # Filter only events mentioning our service
            message = _extract_message(event)
            source = event.SourceName or ""
            if _SERVICE_NAME.lower() not in message.lower() and _SERVICE_NAME.lower() not in source.lower():
                continue

            self._handle_event(eid, log_name, source, message, rec_num)

        self._last_record[log_name] = new_last

    # -- event handling ----------------------------------------------------

    def _handle_event(
        self,
        event_id: int,
        log_name: str,
        source: str,
        message: str,
        record_number: int,
    ) -> None:
        meta = _EVENT_TYPE_MAP.get(event_id)
        if not meta:
            return

        raw_event = {
            "source": source,
            "log": log_name,
            "message": message,
            "record_number": record_number,
            "computer_name": self._computer_name,
        }

        # Determine service_state for 7036
        service_state = None
        if event_id == 7036:
            lower_msg = message.lower()
            if "stopped" in lower_msg:
                service_state = "stopped"
            elif "running" in lower_msg or "started" in lower_msg:
                service_state = "running"

        tamper_payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": event_id,
            "event_type": meta["event_type"],
            "severity": meta["severity"],
            "service_state": service_state,
            "maintenance_window_id": None,
            "classified_as": "tamper_attempt" if event_id == 4656 else None,
            "raw_event": raw_event,
            "component_id": self._component_id,
        }

        # POST 1 — tamper_events
        tamper_event_id = self._post_tamper_event(tamper_payload)

        # POST 2 — behavioral_events (only for 4656)
        if event_id == 4656 and tamper_event_id:
            self._post_behavioral_event(tamper_event_id, message, raw_event)

    def _post_tamper_event(self, payload: dict) -> Optional[str]:
        try:
            resp = requests.post(
                f"{self._base_url}/api/v1/tamper-events",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return data.get("id")
        except Exception as exc:
            logger.warning("Tamper event POST failed: %s", exc)
            return None

    def _post_behavioral_event(
        self,
        tamper_event_id: str,
        message: str,
        raw_event: dict,
    ) -> None:
        # Query active task for context
        task_context = self._get_task_context()
        attempted_by = _extract_username(message)

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "stop_attempt_denied",
            "attempted_by": attempted_by,
            "tamper_event_id": tamper_event_id,
            "task_context": task_context,
            "raw_event": raw_event,
            "component_id": self._component_id,
        }
        try:
            resp = requests.post(
                f"{self._base_url}/api/v1/behavioral-events",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Behavioral event POST failed: %s", exc)

    def _get_task_context(self) -> dict:
        """Fetch the active task and compute timing context."""
        try:
            resp = requests.get(
                f"{self._base_url}/api/v1/tasks/active",
                timeout=5,
            )
            resp.raise_for_status()
            task = resp.json().get("data")
            if not task:
                return {}

            now = datetime.now(timezone.utc)

            started_at_str = task.get("scheduled_start")
            sched_end_str = task.get("scheduled_end")

            started_at = None
            sched_end = None
            if started_at_str:
                started_at = datetime.fromisoformat(
                    started_at_str.replace("Z", "+00:00")
                )
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
            if sched_end_str:
                sched_end = datetime.fromisoformat(
                    sched_end_str.replace("Z", "+00:00")
                )
                if sched_end.tzinfo is None:
                    sched_end = sched_end.replace(tzinfo=timezone.utc)

            minutes_elapsed = None
            minutes_remaining = None
            if started_at:
                minutes_elapsed = int((now - started_at).total_seconds() / 60)
            if sched_end:
                minutes_remaining = max(0, int((sched_end - now).total_seconds() / 60))

            return {
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "task_started_at": started_at_str,
                "task_scheduled_end": sched_end_str,
                "minutes_elapsed": minutes_elapsed,
                "minutes_remaining": minutes_remaining,
            }
        except Exception as exc:
            logger.warning("Failed to fetch task context: %s", exc)
            return {}
