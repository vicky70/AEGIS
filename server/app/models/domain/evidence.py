from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from server.app.core.constants import EvidenceType


class AnalysisResult(BaseModel):
    supports_completion: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class Evidence(BaseModel):
    id: str
    task_id: str
    user_id: str
    type: EvidenceType
    captured_at: datetime
    data: dict[str, Any] = {}
    analysis_result: Optional[AnalysisResult] = None
    retention_until: Optional[datetime] = None
