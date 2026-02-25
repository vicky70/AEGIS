from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from server.app.core.constants import EvidenceType


# ── Request Schemas ───────────────────────────────────────────────

class EvidenceCreate(BaseModel):
    task_id: str
    type: EvidenceType
    data: dict[str, Any] = {}
    captured_at: Optional[datetime] = None


# ── Response Schemas ──────────────────────────────────────────────

class AnalysisResultResponse(BaseModel):
    supports_completion: bool
    confidence: float
    reasoning: str


class EvidenceResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    type: EvidenceType
    captured_at: datetime
    data: dict[str, Any]
    analysis_result: Optional[AnalysisResultResponse]
    retention_until: Optional[datetime]
