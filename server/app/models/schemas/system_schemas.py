from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from server.app.core.constants import (
    ComponentStatus,
    ComponentType,
    EventType,
    PenaltyTriggerType,
    Severity,
)


# ── Heartbeat ─────────────────────────────────────────────────────

class HeartbeatRequest(BaseModel):
    component_id: str
    timestamp: datetime
    sequence_number: int = 0
    status: str = "running"
    hash: Optional[str] = None
    signature: Optional[str] = None


class HeartbeatResponse(BaseModel):
    acknowledged: bool = True
    server_time: datetime


# ── Component Registration ────────────────────────────────────────

class ComponentRegisterRequest(BaseModel):
    component_id: str
    component_type: ComponentType
    device_id: str
    public_key: str
    expected_hash: str


class ComponentAuthenticateRequest(BaseModel):
    component_id: str
    timestamp: datetime
    hash: str
    signature: str


class ComponentResponse(BaseModel):
    id: str
    component_id: str
    component_type: ComponentType
    device_id: str
    registered_at: datetime
    status: ComponentStatus
    last_heartbeat: Optional[datetime]
    consecutive_missed: int


class ComponentTokenResponse(BaseModel):
    token: str
    expires_in: int = 300  # 5 minutes


# ── System Health ─────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "down"
    latency_ms: Optional[float] = None


class SystemHealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    services: list[ServiceHealth]
    components: dict[str, int] = {}  # status -> count


# ── System Events ─────────────────────────────────────────────────

class SystemEventResponse(BaseModel):
    id: str
    timestamp: datetime
    event_type: EventType
    component_id: Optional[str]
    user_id: Optional[str]
    severity: Severity
    details: dict[str, Any]
    acknowledged: bool


# ── Lockdown ──────────────────────────────────────────────────────

class LockdownRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class UnlockRequest(BaseModel):
    trusted_contact_email: str
    verification_code: str


# ── Penalties ─────────────────────────────────────────────────────

class PenaltyResponse(BaseModel):
    id: str
    user_id: str
    triggered_at: datetime
    duration_minutes: int
    reason: str
    trigger_type: PenaltyTriggerType
    trigger_details: dict[str, Any]
    ended_at: Optional[datetime]
    early_release: bool
    early_release_reason: Optional[str]


class ActivePenaltyResponse(BaseModel):
    active: bool
    penalty: Optional[PenaltyResponse] = None
    expires_at: Optional[datetime] = None
    remaining_seconds: Optional[int] = None


class PenaltyAppealRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)
