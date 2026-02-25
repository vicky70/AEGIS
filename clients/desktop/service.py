"""AEGIS Desktop Monitor — Windows Service wrapper.

Integrates with the Windows Service Control Manager via pywin32.
All real work is delegated to the Orchestrator.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

import requests
import yaml

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:
    # Allow import on non-Windows for linting.
    servicemanager = win32event = win32service = win32serviceutil = None  # type: ignore[assignment]

from orchestrator import Orchestrator

logger = logging.getLogger("aegis.service")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class AEGISMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AEGISMonitor"
    _svc_display_name_ = "AEGIS Desktop Monitor"
    _svc_description_ = "AEGIS personal accountability desktop monitor"

    def __init__(self, args: list) -> None:
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._orchestrator: Orchestrator | None = None
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._component_id: str = cfg["component"]["id"]

    # -- Service lifecycle -------------------------------------------------

    def SvcDoRun(self) -> None:
        """Called by SCM when the service starts."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        try:
            self._orchestrator = Orchestrator()
            self._orchestrator.start_all()
        except Exception as exc:
            logger.critical("Failed to start orchestrator: %s", exc)
            self.SvcStop()
            return

        # Block until stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def SvcStop(self) -> None:
        """Called by SCM when the service is asked to stop."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        # First action: report stop to server (synchronous, short timeout)
        try:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "service_stop_requested",
                "event_id": 0,
                "severity": "info",
                "service_state": "stopped",
                "maintenance_window_id": None,
                "classified_as": None,
                "raw_event": {
                    "source": "AEGISMonitorService",
                    "log": "internal",
                    "message": "Service stop requested via SCM",
                    "record_number": 0,
                    "computer_name": "",
                },
                "component_id": self._component_id,
            }
            requests.post(
                f"{self._base_url}/api/v1/tamper-events",
                json=payload,
                timeout=3,
            )
        except Exception as exc:
            # Log to Windows Event Log — never let a failed POST block shutdown
            try:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_WARNING_TYPE,
                    0xF001,
                    (f"Failed to report stop to server: {exc}", "", ""),
                )
            except Exception:
                pass

        # Stop all components
        if self._orchestrator:
            try:
                self._orchestrator.stop_all()
            except Exception as exc:
                logger.error("Error during orchestrator stop: %s", exc)

        # Signal the stop event
        win32event.SetEvent(self.hWaitStop)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AEGISMonitorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AEGISMonitorService)
