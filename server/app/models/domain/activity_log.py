from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InputStats(BaseModel):
    avg_per_minute: float = 0
    min_per_minute: float = 0
    max_per_minute: float = 0


class AppBreakdownEntry(BaseModel):
    app_name: str
    app_category: str  # "productive"|"communication"|"distraction"|"neutral"
    time_spent_seconds: int
    window_titles: list[str] = []
    keyboard: InputStats = InputStats()
    mouse: InputStats = InputStats()


class DeepFocus(BaseModel):
    is_deep_focus: bool = False
    duration_seconds: int = 0
    switch_count: int = 0


class ActivitySession(BaseModel):
    id: str
    task_id: str
    task_title: str
    session_start: datetime
    session_end: datetime
    duration_seconds: int
    idle_seconds: int
    focus_seconds: int
    app_breakdown: list[AppBreakdownEntry] = []
    context_switches: int = 0
    deep_focus: DeepFocus = DeepFocus()
    component_id: str
