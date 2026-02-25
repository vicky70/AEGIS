from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ───────────────────────────────────────────────

class MaintenanceWindowCreate(BaseModel):
    reason: str = Field(..., min_length=1)
    expected_duration_minutes: int = Field(..., ge=1)


class MaintenanceWindowUpdate(BaseModel):
    status: Optional[str] = None
    actual_stop_at: Optional[datetime] = None
    actual_resume_at: Optional[datetime] = None
    total_downtime_seconds: Optional[int] = None


# ── Response Schemas ──────────────────────────────────────────────

class MaintenanceWindowResponse(BaseModel):
    id: str
    declared_at: datetime
    reason: str
    expected_duration_minutes: int
    expires_at: datetime
    status: str
    actual_stop_at: Optional[datetime]
    actual_resume_at: Optional[datetime]
    total_downtime_seconds: Optional[int]
