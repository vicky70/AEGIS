from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from server.app.core.constants import NotificationPreference


# ── Request Schemas ───────────────────────────────────────────────

class NotificationPreferencesUpdate(BaseModel):
    preference: NotificationPreference


class UserSettingsUpdate(BaseModel):
    penalty_duration_minutes: Optional[int] = Field(default=None, ge=1)
    focus_zone_radius_meters: Optional[int] = Field(default=None, ge=1)
    grace_period_seconds: Optional[int] = Field(default=None, ge=0)
    notification_preferences: Optional[NotificationPreferencesUpdate] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = None
    settings: Optional[UserSettingsUpdate] = None


class TrustedContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str
    phone: Optional[str] = None


# ── Response Schemas ──────────────────────────────────────────────

class NotificationPreferencesResponse(BaseModel):
    preference: NotificationPreference


class UserSettingsResponse(BaseModel):
    penalty_duration_minutes: int
    focus_zone_radius_meters: int
    grace_period_seconds: int
    notification_preferences: NotificationPreferencesResponse


class TrustedContactResponse(BaseModel):
    name: str
    email: str
    phone: Optional[str]
    verified: bool


class UserCurrentStateResponse(BaseModel):
    in_penalty_box: bool
    penalty_expires_at: Optional[datetime]
    in_focus_zone: bool
    active_task_id: Optional[str]


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    email: str
    created_at: datetime
    settings: UserSettingsResponse
    trusted_contacts: list[TrustedContactResponse]
    current_state: UserCurrentStateResponse


class UserStatsResponse(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    completion_rate: float = 0.0
    total_penalties: int = 0
    current_streak: int = 0
