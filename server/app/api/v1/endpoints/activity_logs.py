from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_activity_log_service
from server.app.models.schemas.activity_log_schemas import (
    ActivitySessionCreate,
    ActivitySessionResponse,
)
from server.app.models.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.services.activity_log_service import ActivityLogService

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


@router.post("", response_model=SuccessResponse[ActivitySessionResponse], status_code=201)
async def submit_activity_session(
    data: ActivitySessionCreate,
    service: ActivityLogService = Depends(get_activity_log_service),
):
    session = await service.submit_session(data)
    return SuccessResponse(data=session)


@router.get("", response_model=PaginatedResponse[ActivitySessionResponse])
async def list_activity_sessions(
    task_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: ActivityLogService = Depends(get_activity_log_service),
):
    sessions, total = await service.get_sessions(
        task_id=task_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        data=sessions,
        pagination=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get("/{session_id}", response_model=SuccessResponse[ActivitySessionResponse])
async def get_activity_session(
    session_id: str,
    service: ActivityLogService = Depends(get_activity_log_service),
):
    session = await service.get_session(session_id)
    return SuccessResponse(data=session)


@router.post("/batch", response_model=SuccessResponse[list[ActivitySessionResponse]], status_code=201)
async def submit_activity_sessions_batch(
    data: list[ActivitySessionCreate],
    service: ActivityLogService = Depends(get_activity_log_service),
):
    results = []
    for session_data in data:
        session = await service.submit_session(session_data)
        results.append(session)
    return SuccessResponse(data=results)
