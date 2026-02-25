from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from server.app.core.constants import (
    ComponentStatus,
    ComponentType,
    EventType,
    PenaltyTriggerType,
    Severity,
)


class SystemComponent(BaseModel):
    id: str
    component_id: str
    component_type: ComponentType
    device_id: str
    registered_at: datetime
    expected_hash: str
    public_key: str
    last_heartbeat: Optional[datetime] = None
    last_reported_hash: Optional[str] = None
    status: ComponentStatus = ComponentStatus.OFFLINE
    consecutive_missed: int = 0


class SystemEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: EventType
    component_id: Optional[str] = None
    user_id: Optional[str] = None
    severity: Severity
    details: dict[str, Any] = {}
    acknowledged: bool = False


class PenaltyRecord(BaseModel):
    id: str
    user_id: str
    triggered_at: datetime
    duration_minutes: int
    reason: str
    trigger_type: PenaltyTriggerType
    trigger_details: dict[str, Any] = {}
    ended_at: Optional[datetime] = None
    early_release: bool = False
    early_release_reason: Optional[str] = None


    # ActivityLog removed — replaced by ActivitySession in activity_log.py
