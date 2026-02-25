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


class Recurrence(BaseModel):
    pattern: RecurrencePattern
    days: list[int] = []  # 0=Sunday, 6=Saturday
    end_date: Optional[datetime] = None


class VerificationConfig(BaseModel):
    method: VerificationMethod = VerificationMethod.MANUAL
    config: dict[str, Any] = {}
    required_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class VerificationResult(BaseModel):
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    verified_at: datetime
    method_used: str


class Task(BaseModel):
    id: str
    user_id: str
    title: str
    description: str = ""
    category: TaskCategory = TaskCategory.PERSONAL
    priority: int = Field(default=3, ge=1, le=5)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    recurrence: Optional[Recurrence] = None
    verification: VerificationConfig = VerificationConfig()
    status: TaskStatus = TaskStatus.PENDING
    completion_evidence: list[str] = []
    verification_result: Optional[VerificationResult] = None
    failure_count: int = 0
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime
