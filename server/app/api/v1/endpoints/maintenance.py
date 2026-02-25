from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_maintenance_service
from server.app.models.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.models.schemas.maintenance_schemas import (
    MaintenanceWindowCreate,
    MaintenanceWindowResponse,
    MaintenanceWindowUpdate,
)
from server.app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/system/maintenance", tags=["maintenance"])


@router.post("", response_model=SuccessResponse[MaintenanceWindowResponse], status_code=201)
async def declare_maintenance_window(
    data: MaintenanceWindowCreate,
    service: MaintenanceService = Depends(get_maintenance_service),
):
    window = await service.declare_window(data)
    return SuccessResponse(data=window)


@router.get("", response_model=PaginatedResponse[MaintenanceWindowResponse])
async def list_maintenance_windows(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: MaintenanceService = Depends(get_maintenance_service),
):
    windows, total = await service.list_windows(page=page, per_page=per_page)
    return PaginatedResponse(
        data=windows,
        pagination=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get("/active", response_model=SuccessResponse[MaintenanceWindowResponse | None])
async def get_active_maintenance_window(
    service: MaintenanceService = Depends(get_maintenance_service),
):
    window = await service.get_active_or_declared()
    return SuccessResponse(data=window)


@router.get("/{window_id}", response_model=SuccessResponse[MaintenanceWindowResponse])
async def get_maintenance_window(
    window_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
):
    window = await service.get_window(window_id)
    return SuccessResponse(data=window)


@router.patch("/{window_id}", response_model=SuccessResponse[MaintenanceWindowResponse])
async def update_maintenance_window(
    window_id: str,
    data: MaintenanceWindowUpdate,
    service: MaintenanceService = Depends(get_maintenance_service),
):
    window = await service.update_window(window_id, data)
    return SuccessResponse(data=window)
