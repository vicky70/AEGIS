from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from server.app.api.dependencies import (
    get_current_user_id,
    get_evidence_repo,
)
from server.app.core.config import get_settings
from server.app.core.exceptions import EvidenceNotFoundException
from server.app.models.schemas.common import SuccessResponse
from server.app.models.schemas.evidence_schemas import EvidenceCreate, EvidenceResponse
from server.app.repositories.evidence_repository import EvidenceRepository
from server.app.repositories.task_repository import TaskRepository

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("", response_model=SuccessResponse[EvidenceResponse], status_code=201)
async def submit_evidence(
    data: EvidenceCreate,
    user_id: str = Depends(get_current_user_id),
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
):
    settings = get_settings()
    now = datetime.now(timezone.utc)
    doc = {
        "task_id": data.task_id,
        "user_id": user_id,
        "type": data.type.value,
        "captured_at": data.captured_at or now,
        "data": data.data,
        "analysis_result": None,
        "retention_until": now + timedelta(days=settings.aegis.evidence_retention_days),
    }
    evidence_id = await evidence_repo.insert_one(doc)
    evidence = await evidence_repo.find_by_id(evidence_id)

    # Link to task
    task_repo = TaskRepository()
    await task_repo.add_evidence_ref(data.task_id, evidence_id)

    return SuccessResponse(data=evidence)


@router.get("/{evidence_id}", response_model=SuccessResponse[EvidenceResponse])
async def get_evidence(
    evidence_id: str,
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
):
    evidence = await evidence_repo.find_by_id(evidence_id)
    if not evidence:
        raise EvidenceNotFoundException(evidence_id)
    return SuccessResponse(data=evidence)


@router.delete("/{evidence_id}", response_model=SuccessResponse[dict])
async def delete_evidence(
    evidence_id: str,
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
):
    evidence = await evidence_repo.find_by_id(evidence_id)
    if not evidence:
        raise EvidenceNotFoundException(evidence_id)
    await evidence_repo.delete_one(evidence_id)
    return SuccessResponse(data={"deleted": True})
