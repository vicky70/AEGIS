from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from server.app.core.constants import NotificationPreference


class NotificationPreferences(BaseModel):
    preference: NotificationPreference = NotificationPreference.BOTH


class UserSettings(BaseModel):
    penalty_duration_minutes: int = 30
    focus_zone_radius_meters: int = 30
    grace_period_seconds: int = 120
    notification_preferences: NotificationPreferences = NotificationPreferences()


class TrustedContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    verified: bool = False


class UserCurrentState(BaseModel):
    in_penalty_box: bool = False
    penalty_expires_at: Optional[datetime] = None
    in_focus_zone: bool = False
    active_task_id: Optional[str] = None


class User(BaseModel):
    id: str
    username: str
    display_name: str
    email: str
    created_at: datetime
    settings: UserSettings = UserSettings()
    trusted_contacts: list[TrustedContact] = []
    current_state: UserCurrentState = UserCurrentState()
