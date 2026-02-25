from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from server.app.models.schemas.tamper_event_schemas import RawWindowsEventCreate


# ── Nested Schemas ────────────────────────────────────────────────

class TaskContextCreate(BaseModel):
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    task_started_at: Optional[datetime] = None
    task_scheduled_end: Optional[datetime] = None
    minutes_elapsed: Optional[int] = None
    minutes_remaining: Optional[int] = None


# ── Request Schemas ───────────────────────────────────────────────

class BehavioralEventCreate(BaseModel):
    timestamp: datetime
    event_type: str
    attempted_by: str
    tamper_event_id: str
    task_context: TaskContextCreate = TaskContextCreate()
    raw_event: RawWindowsEventCreate
    component_id: str = "desktop_client_main"


# ── Response Schemas ──────────────────────────────────────────────

class BehavioralEventResponse(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    attempted_by: str
    tamper_event_id: str
    task_context: TaskContextCreate
    raw_event: RawWindowsEventCreate
    component_id: str
