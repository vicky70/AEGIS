from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_current_user_id, get_penalty_service
from server.app.models.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.models.schemas.system_schemas import (
    ActivePenaltyResponse,
    PenaltyAppealRequest,
    PenaltyResponse,
)
from server.app.services.penalty_service import PenaltyService

router = APIRouter(prefix="/penalties", tags=["penalties"])


@router.get("/active", response_model=SuccessResponse[ActivePenaltyResponse])
async def get_active_penalty(
    user_id: str = Depends(get_current_user_id),
    service: PenaltyService = Depends(get_penalty_service),
):
    penalty = await service.get_active_penalty(user_id)
    if penalty:
        from datetime import timedelta

        expires_at = penalty["triggered_at"] + timedelta(
            minutes=penalty["duration_minutes"]
        )
        now = datetime.now(timezone.utc)
        remaining = max(0, int((expires_at - now).total_seconds()))
        return SuccessResponse(data=ActivePenaltyResponse(
            active=True,
            penalty=penalty,
            expires_at=expires_at,
            remaining_seconds=remaining,
        ))
    return SuccessResponse(data=ActivePenaltyResponse(active=False))


@router.get("/history", response_model=PaginatedResponse[PenaltyResponse])
async def get_penalty_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: PenaltyService = Depends(get_penalty_service),
):
    penalties, total = await service.get_penalty_history(user_id, page, per_page)
    return PaginatedResponse(
        data=penalties,
        pagination=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.post("/appeal", response_model=SuccessResponse[dict])
async def submit_appeal(
    data: PenaltyAppealRequest,
    user_id: str = Depends(get_current_user_id),
):
    # Placeholder: appeals require review mechanism (future phase)
    return SuccessResponse(data={
        "appeal_submitted": True,
        "reason": data.reason,
        "status": "pending_review",
    })
