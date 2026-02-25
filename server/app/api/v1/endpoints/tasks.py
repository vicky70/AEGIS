from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from server.app.api.dependencies import get_current_user_id, get_task_service
from server.app.core.constants import TaskCategory, TaskStatus
from server.app.models.schemas.common import (
    Meta,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from server.app.models.schemas.task_schemas import (
    TaskCreate,
    TaskResponse,
    TaskSkipRequest,
    TaskUpdate,
)
from server.app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    category: Optional[TaskCategory] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    tasks, total = await service.list_tasks(
        user_id,
        status=status.value if status else None,
        category=category.value if category else None,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        data=tasks,
        pagination=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.post("", response_model=SuccessResponse[TaskResponse], status_code=201)
async def create_task(
    data: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    task = await service.create_task(user_id, data)
    return SuccessResponse(data=task)


@router.get("/upcoming", response_model=SuccessResponse[list[TaskResponse]])
async def get_upcoming_tasks(
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    tasks = await service.get_upcoming(user_id)
    return SuccessResponse(data=tasks)


@router.get("/active", response_model=SuccessResponse[Optional[TaskResponse]])
async def get_active_task(
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    task = await service.get_active_task(user_id)
    return SuccessResponse(data=task)


@router.get("/{task_id}", response_model=SuccessResponse[TaskResponse])
async def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    task = await service.get_task(task_id)
    return SuccessResponse(data=task)


@router.patch("/{task_id}", response_model=SuccessResponse[TaskResponse])
async def update_task(
    task_id: str,
    data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    task = await service.update_task(task_id, data)
    return SuccessResponse(data=task)


@router.delete("/{task_id}", response_model=SuccessResponse[dict])
async def delete_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    await service.delete_task(task_id)
    return SuccessResponse(data={"deleted": True})


@router.post("/{task_id}/start", response_model=SuccessResponse[TaskResponse])
async def start_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    task = await service.start_task(task_id, user_id)
    return SuccessResponse(data=task)


@router.post("/{task_id}/complete", response_model=SuccessResponse[TaskResponse])
async def complete_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    task = await service.complete_task(task_id, user_id)
    return SuccessResponse(data=task)


@router.post("/{task_id}/skip", response_model=SuccessResponse[TaskResponse])
async def skip_task(
    task_id: str,
    data: TaskSkipRequest,
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service),
):
    task = await service.skip_task(task_id, user_id, data.reason)
    return SuccessResponse(data=task)


@router.get("/{task_id}/evidence")
async def get_task_evidence(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    from server.app.repositories.evidence_repository import EvidenceRepository

    # Verify task exists
    await service.get_task(task_id)
    evidence_repo = EvidenceRepository()
    evidence = await evidence_repo.find_by_task(task_id)
    return SuccessResponse(data=evidence)
