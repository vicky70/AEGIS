from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from server.app.models.domain.tamper_event import RawWindowsEvent


class TaskContext(BaseModel):
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    task_started_at: Optional[datetime] = None
    task_scheduled_end: Optional[datetime] = None
    minutes_elapsed: Optional[int] = None
    minutes_remaining: Optional[int] = None


class BehavioralEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    attempted_by: str
    tamper_event_id: str
    task_context: TaskContext = TaskContext()
    raw_event: RawWindowsEvent
    component_id: str
