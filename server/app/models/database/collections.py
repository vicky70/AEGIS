"""MongoDB collection names and index definitions."""

from __future__ import annotations

# Collection names
USERS = "users"
TASKS = "tasks"
EVIDENCE = "evidence"
ACTIVITY_LOGS = "activity_logs"
SYSTEM_COMPONENTS = "system_components"
SYSTEM_EVENTS = "system_events"
PENALTY_HISTORY = "penalty_history"
TAMPER_EVENTS = "tamper_events"
BEHAVIORAL_EVENTS = "behavioral_events"
MAINTENANCE_WINDOWS = "maintenance_windows"

# Index definitions: list of (collection, keys, kwargs)
INDEXES: list[tuple[str, list[tuple[str, int]], dict]] = [
    # Tasks
    (TASKS, [("user_id", 1), ("scheduled_start", 1)], {}),
    (TASKS, [("user_id", 1), ("status", 1)], {}),
    # Evidence
    (EVIDENCE, [("task_id", 1)], {}),
    # Activity logs (session-based)
    (ACTIVITY_LOGS, [("session_start", -1)], {}),
    (ACTIVITY_LOGS, [("task_id", 1)], {}),
    # System components
    (SYSTEM_COMPONENTS, [("component_id", 1)], {"unique": True}),
    # System events
    (SYSTEM_EVENTS, [("timestamp", -1), ("severity", 1)], {}),
    # Penalty history
    (PENALTY_HISTORY, [("user_id", 1), ("triggered_at", -1)], {}),
    # Users
    (USERS, [("username", 1)], {"unique": True}),
    # Tamper events
    (TAMPER_EVENTS, [("timestamp", -1)], {}),
    (TAMPER_EVENTS, [("event_type", 1), ("timestamp", -1)], {}),
    (TAMPER_EVENTS, [("classified_as", 1), ("timestamp", -1)], {}),
    # Behavioral events
    (BEHAVIORAL_EVENTS, [("timestamp", -1)], {}),
    (BEHAVIORAL_EVENTS, [("event_type", 1), ("timestamp", -1)], {}),
    (BEHAVIORAL_EVENTS, [("task_context.task_id", 1)], {}),
    # Maintenance windows
    (MAINTENANCE_WINDOWS, [("status", 1), ("expires_at", 1)], {}),
    (MAINTENANCE_WINDOWS, [("declared_at", -1)], {}),
]
