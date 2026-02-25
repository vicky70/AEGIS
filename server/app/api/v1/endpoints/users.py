from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.dependencies import (
    get_current_user_id,
    get_penalty_repo,
    get_task_service,
    get_user_repo,
)
from server.app.core.constants import TaskStatus
from server.app.core.exceptions import UserNotFoundException
from server.app.models.schemas.common import SuccessResponse
from server.app.models.schemas.user_schemas import (
    UserResponse,
    UserSettingsUpdate,
    UserStatsResponse,
    UserUpdate,
    UserCurrentStateResponse,
)
from server.app.repositories.system_repository import PenaltyRepository
from server.app.repositories.user_repository import UserRepository
from server.app.services.task_service import TaskService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)
    return SuccessResponse(data=user)


@router.patch("/me", response_model=SuccessResponse[UserResponse])
async def update_current_user(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)

    update: dict = {}
    if data.display_name is not None:
        update["display_name"] = data.display_name
    if data.email is not None:
        update["email"] = data.email

    if data.settings:
        settings_update = data.settings.model_dump(exclude_unset=True)
        if "notification_preferences" in settings_update and settings_update["notification_preferences"]:
            settings_update["notification_preferences"] = data.settings.notification_preferences.model_dump()
        if settings_update:
            await user_repo.update_settings(user_id, settings_update)

    if update:
        user = await user_repo.update_one(user_id, update)
    else:
        user = await user_repo.find_by_id(user_id)

    return SuccessResponse(data=user)


@router.get("/me/state", response_model=SuccessResponse[UserCurrentStateResponse])
async def get_user_state(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise UserNotFoundException(user_id)
    return SuccessResponse(data=user.get("current_state", {}))


@router.get("/me/stats", response_model=SuccessResponse[UserStatsResponse])
async def get_user_stats(
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
    penalty_repo: PenaltyRepository = Depends(get_penalty_repo),
):
    task_stats = await task_service.get_user_stats(user_id)
    total_penalties = await penalty_repo.count_by_user(user_id)

    total = sum(task_stats.values())
    completed = task_stats.get(TaskStatus.COMPLETED, 0)
    failed = task_stats.get(TaskStatus.FAILED, 0)
    skipped = task_stats.get(TaskStatus.SKIPPED, 0)

    return SuccessResponse(data=UserStatsResponse(
        total_tasks=total,
        completed_tasks=completed,
        failed_tasks=failed,
        skipped_tasks=skipped,
        completion_rate=completed / total if total > 0 else 0.0,
        total_penalties=total_penalties,
    ))
