from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_integrity_service
from server.app.core.constants import Severity
from server.app.models.schemas.common import SuccessResponse
from server.app.models.schemas.system_schemas import (
    ComponentRegisterRequest,
    ComponentResponse,
    ComponentTokenResponse,
    LockdownRequest,
    ServiceHealth,
    SystemEventResponse,
    SystemHealthResponse,
    UnlockRequest,
)
from server.app.models.database.connection import Database
from server.app.repositories.system_repository import SystemEventRepository
from server.app.services.integrity_service import IntegrityService

router = APIRouter(prefix="/system", tags=["system"])

_start_time = time.time()


@router.get("/health", response_model=SuccessResponse[SystemHealthResponse])
async def system_health(
    service: IntegrityService = Depends(get_integrity_service),
):
    db_health = await Database.check_health()
    services = []
    for name, status in db_health.items():
        services.append(ServiceHealth(name=name, status=status))

    status_counts = await service.get_status_counts()

    overall = "healthy"
    if any(s.status != "healthy" for s in services):
        overall = "degraded"
    if all(s.status == "down" for s in services):
        overall = "down"

    return SuccessResponse(data=SystemHealthResponse(
        status=overall,
        uptime_seconds=time.time() - _start_time,
        services=services,
        components=status_counts,
    ))


@router.get("/components", response_model=SuccessResponse[list[ComponentResponse]])
async def list_components(
    service: IntegrityService = Depends(get_integrity_service),
):
    components = await service.list_components()
    return SuccessResponse(data=components)


@router.get(
    "/components/{component_id}",
    response_model=SuccessResponse[ComponentResponse],
)
async def get_component(
    component_id: str,
    service: IntegrityService = Depends(get_integrity_service),
):
    component = await service.get_component(component_id)
    return SuccessResponse(data=component)


@router.get("/events", response_model=SuccessResponse[list[SystemEventResponse]])
async def get_events(
    severity: Optional[Severity] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    event_repo = SystemEventRepository()
    events = await event_repo.get_recent(
        severity=severity.value if severity else None,
        limit=limit,
    )
    return SuccessResponse(data=events)


@router.post("/lockdown", response_model=SuccessResponse[dict])
async def trigger_lockdown(
    data: LockdownRequest,
    service: IntegrityService = Depends(get_integrity_service),
):
    await service.trigger_lockdown(data.reason)
    return SuccessResponse(data={"lockdown": True, "reason": data.reason})


@router.post("/unlock", response_model=SuccessResponse[dict])
async def unlock_system(
    data: UnlockRequest,
):
    # Placeholder: in production this requires trusted contact verification
    return SuccessResponse(data={"unlocked": True})


@router.post(
    "/components/register",
    response_model=SuccessResponse[ComponentResponse],
    status_code=201,
)
async def register_component(
    data: ComponentRegisterRequest,
    service: IntegrityService = Depends(get_integrity_service),
):
    component = await service.register_component(data.model_dump())
    return SuccessResponse(data=component)
