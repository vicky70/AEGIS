from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MaintenanceWindow(BaseModel):
    id: str
    declared_at: datetime
    reason: str
    expected_duration_minutes: int
    expires_at: datetime
    status: str  # "declared"|"active"|"completed"|"expired"
    actual_stop_at: Optional[datetime] = None
    actual_resume_at: Optional[datetime] = None
    total_downtime_seconds: Optional[int] = None
