from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Nested Schemas ────────────────────────────────────────────────

class InputStatsCreate(BaseModel):
    avg_per_minute: float = 0
    min_per_minute: float = 0
    max_per_minute: float = 0


class AppBreakdownCreate(BaseModel):
    app_name: str
    app_category: str  # "productive"|"communication"|"distraction"|"neutral"
    time_spent_seconds: int
    window_titles: list[str] = []
    keyboard: InputStatsCreate = InputStatsCreate()
    mouse: InputStatsCreate = InputStatsCreate()


class DeepFocusCreate(BaseModel):
    is_deep_focus: bool = False
    duration_seconds: int = 0
    switch_count: int = 0


# ── Request Schemas ───────────────────────────────────────────────

class ActivitySessionCreate(BaseModel):
    task_id: str
    task_title: str
    session_start: datetime
    session_end: datetime
    duration_seconds: int
    idle_seconds: int
    focus_seconds: int
    app_breakdown: list[AppBreakdownCreate] = []
    context_switches: int = 0
    deep_focus: DeepFocusCreate = DeepFocusCreate()
    component_id: str = "desktop_client_main"


# ── Response Schemas ──────────────────────────────────────────────

class ActivitySessionResponse(BaseModel):
    id: str
    task_id: str
    task_title: str
    session_start: datetime
    session_end: datetime
    duration_seconds: int
    idle_seconds: int
    focus_seconds: int
    app_breakdown: list[AppBreakdownCreate]
    context_switches: int
    deep_focus: DeepFocusCreate
    component_id: str
