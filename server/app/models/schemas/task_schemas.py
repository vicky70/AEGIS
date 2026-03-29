from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from server.app.core.constants import (
    IST,
    RecurrencePattern,
    TaskCategory,
    TaskStatus,
    VerificationMethod,
)


# ── Helpers ──────────────────────────────────────────────────────

def _ensure_tz_aware(v: datetime) -> datetime:
    """Reject naive datetimes; input MUST be timezone-aware."""
    if v.tzinfo is None:
        raise ValueError(
            "Datetime must be timezone-aware (include offset, e.g. +05:30 or Z)."
        )
    return v


def _utc_to_ist(v: datetime | None) -> datetime | None:
    """Convert a UTC datetime to Asia/Kolkata (+05:30) for API responses."""
    if v is None:
        return None
    # If naive (e.g. from legacy data), assume UTC
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(IST)


# ── Request Schemas ───────────────────────────────────────────────

class RecurrenceCreate(BaseModel):
    pattern: RecurrencePattern
    days: list[int] = []
    end_date: Optional[datetime] = None

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime):
            _ensure_tz_aware(v)
        return v


class VerificationConfigCreate(BaseModel):
    method: VerificationMethod = VerificationMethod.MANUAL
    config: dict[str, Any] = {}
    required_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category: TaskCategory = TaskCategory.PERSONAL
    priority: int = Field(default=3, ge=1, le=5)
    scheduled_start: datetime = Field(...)
    scheduled_end: datetime = Field(...)
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    recurrence: Optional[RecurrenceCreate] = None
    verification: VerificationConfigCreate = Field(...)
    tags: list[str] = []

    @field_validator("scheduled_start", "scheduled_end", mode="before")
    @classmethod
    def check_tz_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime):
            _ensure_tz_aware(v)
        return v

    @model_validator(mode="after")
    def validate_schedule(self) -> "TaskCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[TaskCategory] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    recurrence: Optional[RecurrenceCreate] = None
    verification: Optional[VerificationConfigCreate] = None
    tags: Optional[list[str]] = None

    @field_validator("scheduled_start", "scheduled_end", mode="before")
    @classmethod
    def check_tz_aware(cls, v: Any) -> Any:
        if v is not None and isinstance(v, datetime):
            _ensure_tz_aware(v)
        return v

    @model_validator(mode="after")
    def validate_schedule(self) -> "TaskUpdate":
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_end <= self.scheduled_start:
                raise ValueError("scheduled_end must be after scheduled_start")
        return self


class TaskSkipRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# ── Response Schemas ──────────────────────────────────────────────

class VerificationResultResponse(BaseModel):
    verified: bool
    confidence: float
    verified_at: datetime
    method_used: str

    @field_validator("verified_at", mode="before")
    @classmethod
    def convert_verified_at(cls, v: Any) -> Any:
        if isinstance(v, datetime):
            return _utc_to_ist(v)
        return v


class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: TaskCategory
    priority: int
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    duration_minutes: Optional[int]
    recurrence: Optional[RecurrenceCreate]
    verification: VerificationConfigCreate
    status: TaskStatus
    completion_evidence: list[str]
    verification_result: Optional[VerificationResultResponse]
    failure_count: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "scheduled_start", "scheduled_end", "created_at", "updated_at",
        mode="before",
    )
    @classmethod
    def convert_to_ist(cls, v: Any) -> Any:
        """Convert stored UTC datetimes to Asia/Kolkata for API output."""
        if isinstance(v, datetime):
            return _utc_to_ist(v)
        return v


# ── Query Filters ─────────────────────────────────────────────────

class TaskFilter(BaseModel):
    status: Optional[TaskStatus] = None
    category: Optional[TaskCategory] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[list[str]] = None
