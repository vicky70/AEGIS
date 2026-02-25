from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_tamper_event_service
from server.app.models.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.models.schemas.tamper_event_schemas import (
    TamperEventCreate,
    TamperEventResponse,
)
from server.app.services.tamper_event_service import TamperEventService

router = APIRouter(prefix="/tamper-events", tags=["tamper-events"])


@router.post("", response_model=SuccessResponse[TamperEventResponse], status_code=201)
async def report_tamper_event(
    data: TamperEventCreate,
    service: TamperEventService = Depends(get_tamper_event_service),
):
    event = await service.report_event(data)
    return SuccessResponse(data=event)


@router.get("", response_model=PaginatedResponse[TamperEventResponse])
async def list_tamper_events(
    event_type: Optional[str] = None,
    classified_as: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: TamperEventService = Depends(get_tamper_event_service),
):
    events, total = await service.get_events(
        event_type=event_type,
        classified_as=classified_as,
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


@router.get("/{event_id}", response_model=SuccessResponse[TamperEventResponse])
async def get_tamper_event(
    event_id: str,
    service: TamperEventService = Depends(get_tamper_event_service),
):
    event = await service.get_event(event_id)
    return SuccessResponse(data=event)
