from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_behavioral_event_service
from server.app.models.schemas.behavioral_event_schemas import (
    BehavioralEventCreate,
    BehavioralEventResponse,
)
from server.app.models.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.services.behavioral_event_service import BehavioralEventService

router = APIRouter(prefix="/behavioral-events", tags=["behavioral-events"])


@router.post("", response_model=SuccessResponse[BehavioralEventResponse], status_code=201)
async def report_behavioral_event(
    data: BehavioralEventCreate,
    service: BehavioralEventService = Depends(get_behavioral_event_service),
):
    event = await service.report_event(data)
    return SuccessResponse(data=event)


@router.get("", response_model=PaginatedResponse[BehavioralEventResponse])
async def list_behavioral_events(
    event_type: Optional[str] = None,
    task_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: BehavioralEventService = Depends(get_behavioral_event_service),
):
    events, total = await service.get_events(
        event_type=event_type,
        task_id=task_id,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        data=events,
        pagination=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get("/{event_id}", response_model=SuccessResponse[BehavioralEventResponse])
async def get_behavioral_event(
    event_id: str,
    service: BehavioralEventService = Depends(get_behavioral_event_service),
):
    event = await service.get_event(event_id)
    return SuccessResponse(data=event)
