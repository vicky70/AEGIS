"""AEGIS Desktop Monitor — Core activity tracker.

Polls the active window every *poll_interval_seconds*, records raw data points,
and collapses them into task-bounded session documents when a task's
scheduled_end is reached or the service is stopping.
"""

from __future__ import annotations

import logging
import os
import sys
import queue
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

import psutil
import requests
import yaml

try:
    import win32api
    import win32gui
    import win32process
except ImportError:
    # Allow import on non-Windows for linting; will fail at runtime.
    win32api = win32gui = win32process = None  # type: ignore[assignment]

from pynput import keyboard as kb
from pynput import mouse as ms

from classifier import classify

logger = logging.getLogger("aegis.activity_tracker")

if getattr(sys, 'frozen', False):
    _CONFIG_PATH = r"C:\ProgramData\AEGIS\config.yaml"
else:
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Input rate counters (keyboard / mouse)
# ---------------------------------------------------------------------------

class _InputCounter:
    """Thread-safe counter for keyboard and mouse events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def increment(self) -> None:
        with self._lock:
            self._count += 1

    def read_and_reset(self) -> int:
        with self._lock:
            val = self._count
            self._count = 0
            return val


# ---------------------------------------------------------------------------
# Activity Tracker
# ---------------------------------------------------------------------------

class ActivityTracker:
    """Collects window activity and builds task-bounded session documents."""

    def __init__(self) -> None:
        cfg = _load_config()
        self._base_url: str = cfg["server"]["base_url"]
        self._component_id: str = cfg["component"]["id"]
        self._poll_interval: int = cfg["activity"]["poll_interval_seconds"]
        self._idle_threshold: int = cfg["activity"]["idle_threshold_seconds"]

        # Threading
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Session output queue
        self._completed: queue.Queue[dict] = queue.Queue()

        # Input listeners
        self._kb_counter = _InputCounter()
        self._ms_counter = _InputCounter()
        self._kb_listener: Optional[kb.Listener] = None
        self._ms_listener: Optional[ms.Listener] = None

        # Active task state
        self._task: Optional[dict] = None
        self._last_task_query: float = 0.0

        # Raw poll buffer for the current session
        self._raw_polls: list[dict] = []
        self._session_start: Optional[datetime] = None
        self._context_switches: int = 0
        self._prev_app: Optional[str] = None

        # Fallback max session duration (2 hours)
        self._max_session_seconds = 2 * 60 * 60

    # -- public API --------------------------------------------------------

    def start(self) -> None:
        """Start the polling thread and input listeners."""
        self._stop_event.clear()
        self._start_input_listeners()
        self._thread = threading.Thread(
            target=self._run, name="ActivityTracker", daemon=True
        )
        self._thread.start()
        logger.info("ActivityTracker started")

    def stop(self) -> None:
        """Signal stop and wait for the polling thread to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15)
        self._stop_input_listeners()
        logger.info("ActivityTracker stopped")

    def get_completed_sessions(self) -> list[dict]:
        """Drain and return all completed session dicts."""
        sessions: list[dict] = []
        while not self._completed.empty():
            try:
                sessions.append(self._completed.get_nowait())
            except queue.Empty:
                break
        return sessions

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- input listeners ---------------------------------------------------

    def _start_input_listeners(self) -> None:
        self._kb_listener = kb.Listener(on_press=lambda _: self._kb_counter.increment())
        self._ms_listener = ms.Listener(
            on_move=lambda *_: self._ms_counter.increment(),
            on_click=lambda *_: self._ms_counter.increment(),
            on_scroll=lambda *_: self._ms_counter.increment(),
        )
        self._kb_listener.start()
        self._ms_listener.start()

    def _stop_input_listeners(self) -> None:
        if self._kb_listener:
            self._kb_listener.stop()
        if self._ms_listener:
            self._ms_listener.stop()

    # -- task query --------------------------------------------------------

    def _query_active_task(self) -> None:
        """GET /api/v1/tasks/active — refresh every 60 s."""
        now = time.time()
        if now - self._last_task_query < 60 and self._task is not None:
            return
        self._last_task_query = now
        try:
            resp = requests.get(
                f"{self._base_url}/api/v1/tasks/active",
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json().get("data")
            if data:
                self._task = data
            else:
                self._task = None
        except Exception as exc:
            logger.warning("Failed to query active task: %s", exc)

    # -- window polling ----------------------------------------------------

    @staticmethod
    def _get_foreground_info() -> tuple[str, str]:
        """Return (app_name, window_title) for the current foreground window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return ("", "")
            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                app_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = ""
            return (app_name, title)
        except Exception:
            return ("", "")

    def _is_idle(self) -> bool:
        """Return True if user has been idle longer than threshold."""
        try:
            last_input = win32api.GetLastInputInfo()
            tick = win32api.GetTickCount()
            idle_ms = tick - last_input
            return (idle_ms / 1000) > self._idle_threshold
        except Exception:
            return False

    # -- main loop ---------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._query_active_task()

            if self._task is None:
                # No active task — wait and retry
                self._stop_event.wait(self._poll_interval)
                continue

            # Start a new session if none is running
            if self._session_start is None:
                self._session_start = datetime.now(timezone.utc)
                self._raw_polls.clear()
                self._context_switches = 0
                self._prev_app = None

            # Collect one data point
            app_name, title = self._get_foreground_info()
            idle = self._is_idle()
            kb_count = self._kb_counter.read_and_reset()
            ms_count = self._ms_counter.read_and_reset()
            category = classify(app_name) if app_name else "neutral"

            # Context switch detection
            if app_name and app_name != self._prev_app and self._prev_app is not None:
                self._context_switches += 1
            if app_name:
                self._prev_app = app_name

            self._raw_polls.append(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "app_name": app_name,
                    "app_category": category,
                    "window_title": title,
                    "idle": idle,
                    "keyboard_count": kb_count,
                    "mouse_count": ms_count,
                }
            )

            # Check session break conditions
            should_close = False

            # Condition 1: scheduled_end reached
            if self._task and self._task.get("scheduled_end"):
                try:
                    sched_end_str = self._task["scheduled_end"]
                    if isinstance(sched_end_str, str):
                        sched_end = datetime.fromisoformat(
                            sched_end_str.replace("Z", "+00:00")
                        )
                        if sched_end.tzinfo is None:
                            sched_end = sched_end.replace(tzinfo=timezone.utc)
                    else:
                        sched_end = sched_end_str
                    if datetime.now(timezone.utc) >= sched_end:
                        should_close = True
                except Exception as e:
                    logger.exception("time failed timezone problem.")
                    pass

            # Condition 2: stop event
            if self._stop_event.is_set():
                should_close = True

            # Fallback: max session duration
            if self._session_start:
                elapsed = (datetime.now(timezone.utc) - self._session_start).total_seconds()
                if elapsed >= self._max_session_seconds:
                    should_close = True

            if should_close:
                self._close_session()
                # Re-query task for next iteration
                self._last_task_query = 0.0
                if self._stop_event.is_set():
                    break

            self._stop_event.wait(self._poll_interval)

        # Flush any remaining session on shutdown
        if self._raw_polls:
            self._close_session()

    # -- session collapse --------------------------------------------------

    def _close_session(self) -> None:
        """Collapse raw polls into a single session document and enqueue it."""
        if not self._raw_polls:
            return

        now = datetime.now(timezone.utc)
        session_start = self._session_start or self._raw_polls[0]["timestamp"]
        session_end = now
        duration = int((session_end - session_start).total_seconds())

        # Idle seconds
        idle_polls = sum(1 for p in self._raw_polls if p["idle"])
        idle_seconds = idle_polls * self._poll_interval
        focus_seconds = max(0, duration - idle_seconds)

        # App breakdown
        app_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "time_polls": 0,
                "titles": set(),
                "kb_counts": [],
                "ms_counts": [],
                "category": "neutral",
            }
        )
        for poll in self._raw_polls:
            name = poll["app_name"] or "unknown"
            entry = app_data[name]
            entry["time_polls"] += 1
            entry["category"] = poll["app_category"]
            if poll["window_title"]:
                entry["titles"].add(poll["window_title"])
            entry["kb_counts"].append(poll["keyboard_count"])
            entry["ms_counts"].append(poll["mouse_count"])

        app_breakdown = []
        for app_name, data in app_data.items():
            polls = data["time_polls"]
            time_spent = polls * self._poll_interval

            def _stats(counts: list[int]) -> dict:
                if not counts:
                    return {"avg_per_minute": 0, "min_per_minute": 0, "max_per_minute": 0}
                # Convert from per-poll-interval to per-minute
                factor = 60.0 / self._poll_interval
                per_min = [c * factor for c in counts]
                return {
                    "avg_per_minute": round(sum(per_min) / len(per_min), 1),
                    "min_per_minute": round(min(per_min), 1),
                    "max_per_minute": round(max(per_min), 1),
                }

            app_breakdown.append(
                {
                    "app_name": app_name,
                    "app_category": data["category"],
                    "time_spent_seconds": time_spent,
                    "window_titles": list(data["titles"]),
                    "keyboard": _stats(data["kb_counts"]),
                    "mouse": _stats(data["ms_counts"]),
                }
            )

        # Deep focus
        is_deep_focus = focus_seconds > 1500 and self._context_switches < 5

        task_id = self._task["id"] if self._task else "unknown"
        task_title = self._task.get("title", "Unknown Task") if self._task else "Unknown Task"

        session_doc = {
            "task_id": task_id,
            "task_title": task_title,
            "session_start": session_start.isoformat(),
            "session_end": session_end.isoformat(),
            "duration_seconds": duration,
            "idle_seconds": idle_seconds,
            "focus_seconds": focus_seconds,
            "context_switches": self._context_switches,
            "app_breakdown": app_breakdown,
            "deep_focus": {
                "is_deep_focus": is_deep_focus,
                "duration_seconds": focus_seconds,
                "switch_count": self._context_switches,
            },
            "component_id": self._component_id,
        }

        self._completed.put(session_doc)
        logger.info(
            "Session closed: task=%s duration=%ds apps=%d",
            task_id,
            duration,
            len(app_breakdown),
        )

        # Reset for next session
        self._raw_polls.clear()
        self._session_start = None
        self._context_switches = 0
        self._prev_app = None
