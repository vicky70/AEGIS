"""AEGIS Desktop Monitor — Watchdog.

Standalone script invoked every 60 seconds by Windows Task Scheduler.
Runs once top-to-bottom, then exits.  Independent of the service process.
"""

from __future__ import annotations

import logging
import os
import socket
import sys
from datetime import datetime, timezone, timedelta

import requests
import yaml

try:
    import win32evtlog
    import win32serviceutil
    import win32service
except ImportError:
    win32evtlog = win32serviceutil = win32service = None  # type: ignore[assignment]

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
_FALLBACK_LOG = r"C:\ProgramData\AEGIS\watchdog.log"
_SERVICE_NAME = "AEGISMonitor"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("aegis.watchdog")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _fallback_log(msg: str) -> None:
    """Append a timestamped line to the local fallback log."""
    try:
        os.makedirs(os.path.dirname(_FALLBACK_LOG), exist_ok=True)
        with open(_FALLBACK_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def _post_tamper(base_url: str, payload: dict) -> bool:
    """POST to tamper-events. Returns True on success."""
    try:
        resp = requests.post(
            f"{base_url}/api/v1/tamper-events",
            json=payload,
            timeout=5,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        _fallback_log(f"POST tamper-events failed: {exc}")
        return False


def main() -> None:
    try:
        cfg = _load_config()
    except Exception as exc:
        _fallback_log(f"Cannot load config: {exc}")
        sys.exit(1)

    base_url = cfg["server"]["base_url"]
    component_id = cfg["component"]["id"]
    computer_name = socket.gethostname()

    # ── 1. Check service status ──────────────────────────────────────
    try:
        status = win32serviceutil.QueryServiceStatus(_SERVICE_NAME)
        svc_state = status[1]  # SERVICE_STATUS.dwCurrentState
    except Exception as exc:
        _fallback_log(f"Cannot query service status: {exc}")
        svc_state = 0  # Treat as not running

    if svc_state == win32service.SERVICE_RUNNING:
        # Service is running — nothing to do
        sys.exit(0)

    # ── 2. Service is NOT running — classify the stop ────────────────
    try:
        resp = requests.get(
            f"{base_url}/api/v1/system/maintenance/active",
            timeout=5,
        )
        resp.raise_for_status()
        maint_data = resp.json().get("data")
    except Exception as exc:
        _fallback_log(f"Cannot check maintenance window: {exc}")
        maint_data = None

    if maint_data:
        classified_as = "intended_maintenance"
        severity = "info"
    else:
        classified_as = "unexpected_stop"
        severity = "critical"

    _post_tamper(base_url, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_id": 7036,
        "event_type": "service_state_change",
        "severity": severity,
        "service_state": "stopped",
        "maintenance_window_id": None,
        "classified_as": classified_as,
        "raw_event": {
            "source": "AEGISWatchdog",
            "log": "watchdog",
            "message": f"Service {_SERVICE_NAME} found stopped (classified: {classified_as})",
            "record_number": 0,
            "computer_name": computer_name,
        },
        "component_id": component_id,
    })

    # ── 3. Attempt restart ───────────────────────────────────────────
    try:
        win32serviceutil.StartService(_SERVICE_NAME)
        logger.info("Service restart initiated")
        _post_tamper(base_url, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": 0,
            "event_type": "service_restarted",
            "severity": "info",
            "service_state": "running",
            "maintenance_window_id": None,
            "classified_as": None,
            "raw_event": {
                "source": "AEGISWatchdog",
                "log": "watchdog",
                "message": f"Service {_SERVICE_NAME} restarted by watchdog",
                "record_number": 0,
                "computer_name": computer_name,
            },
            "component_id": component_id,
        })
    except Exception as exc:
        logger.error("Service restart failed: %s", exc)
        _post_tamper(base_url, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": 0,
            "event_type": "restart_failed",
            "severity": "critical",
            "service_state": "stopped",
            "maintenance_window_id": None,
            "classified_as": None,
            "raw_event": {
                "source": "AEGISWatchdog",
                "log": "watchdog",
                "message": f"Service {_SERVICE_NAME} restart failed: {exc}",
                "record_number": 0,
                "computer_name": computer_name,
            },
            "component_id": component_id,
        })

    # ── 4. Check for startup-type changes (Event ID 7040) ────────────
    try:
        handle = win32evtlog.OpenEventLog(None, "System")
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        events = win32evtlog.ReadEventLog(handle, flags, 0)
        win32evtlog.CloseEventLog(handle)

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)

        for event in events:
            eid = event.EventID & 0xFFFF
            if eid != 7040:
                continue
            # Check if event is recent enough
            event_time = event.TimeGenerated
            if hasattr(event_time, "replace"):
                event_time = event_time.replace(tzinfo=timezone.utc)
            if event_time < cutoff:
                break  # Events are in reverse chronological order

            msg_parts = event.StringInserts or []
            message = " | ".join(str(s) for s in msg_parts)
            if _SERVICE_NAME.lower() not in message.lower():
                continue

            _post_tamper(base_url, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": 7040,
                "event_type": "startup_type_changed",
                "severity": "critical",
                "service_state": None,
                "maintenance_window_id": None,
                "classified_as": "tamper_attempt",
                "raw_event": {
                    "source": event.SourceName or "Service Control Manager",
                    "log": "System",
                    "message": message,
                    "record_number": event.RecordNumber,
                    "computer_name": computer_name,
                },
                "component_id": component_id,
            })
            break  # Only report the first recent match

    except Exception as exc:
        _fallback_log(f"Event log check failed: {exc}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _fallback_log(f"Watchdog unhandled error: {exc}")
        sys.exit(1)
