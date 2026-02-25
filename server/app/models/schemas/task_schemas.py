from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from server.app.core.constants import (
    RecurrencePattern,
    TaskCategory,
    TaskStatus,
    VerificationMethod,
)


# ── Request Schemas ───────────────────────────────────────────────

class RecurrenceCreate(BaseModel):
    pattern: RecurrencePattern
    days: list[int] = []
    end_date: Optional[datetime] = None


class VerificationConfigCreate(BaseModel):
    method: VerificationMethod = VerificationMethod.MANUAL
    config: dict[str, Any] = {}
    required_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category: TaskCategory = TaskCategory.PERSONAL
    priority: int = Field(default=3, ge=1, le=5)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    recurrence: Optional[RecurrenceCreate] = None
    verification: VerificationConfigCreate = VerificationConfigCreate()
    tags: list[str] = []


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


class TaskSkipRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# ── Response Schemas ──────────────────────────────────────────────

class VerificationResultResponse(BaseModel):
    verified: bool
    confidence: float
    verified_at: datetime
    method_used: str


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


# ── Query Filters ─────────────────────────────────────────────────

class TaskFilter(BaseModel):
    status: Optional[TaskStatus] = None
    category: Optional[TaskCategory] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[list[str]] = None
