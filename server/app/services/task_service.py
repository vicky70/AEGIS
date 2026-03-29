from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from server.app.core.constants import (
    CHANNEL_TASKS,
    EventType,
    Severity,
    TaskStatus,
)
from server.app.core.exceptions import (
    TaskAlreadyActiveException,
    TaskNotFoundException,
    ValidationException,
)
from server.app.models.schemas.task_schemas import TaskCreate, TaskUpdate
from server.app.repositories.task_repository import TaskRepository
from server.app.repositories.system_repository import SystemEventRepository
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.task")


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository | None = None,
        event_repo: SystemEventRepository | None = None,
    ):
        self.task_repo = task_repo or TaskRepository()
        self.event_repo = event_repo or SystemEventRepository()
        self.event_bus = EventBus.get()

    async def create_task(self, user_id: str, data: TaskCreate) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        # 1. Title cannot be empty/whitespace
        if not data.title.strip():
            raise ValidationException("Title cannot be empty or whitespace.")

        # 2. Convert to UTC for consistent comparison and storage
        start_utc = data.scheduled_start.astimezone(timezone.utc)
        end_utc = data.scheduled_end.astimezone(timezone.utc)

        # 3. scheduled_start must be in the future (full datetime check)
        if start_utc <= now:
            raise ValidationException("scheduled_start must be in the future.")

        # 4. scheduled_end must be after scheduled_start
        if end_utc <= start_utc:
            raise ValidationException("scheduled_end must be after scheduled_start.")

        # 5. Conflict check (use UTC values for DB query)
        conflicting = await self.task_repo.find_conflicting_task(
            start_utc, end_utc
        )
        if conflicting:
            raise ValidationException(
                f"Time conflict with existing task '{conflicting['title']}'. "
                f"A 1-minute gap is required between tasks."
            )

        doc = {
            "user_id": user_id,
            "title": data.title.strip(),
            "description": data.description,
            "category": data.category.value,
            "priority": data.priority,
            "scheduled_start": start_utc,
            "scheduled_end": end_utc,
            "duration_minutes": data.duration_minutes,
            "recurrence": data.recurrence.model_dump() if data.recurrence else None,
            "verification": data.verification.model_dump(),
            "status": TaskStatus.PENDING,
            "completion_evidence": [],
            "verification_result": None,
            "failure_count": 0,
            "tags": data.tags,
            "created_at": now,
            "updated_at": now,
        }

        task_id = await self.task_repo.insert_one(doc)
        task = await self.task_repo.find_by_id(task_id)
        logger.info("Task created: %s for user %s", task_id, user_id)

        await self.event_bus.emit(CHANNEL_TASKS, {
            "event_type": "task_created",
            "task_id": task_id,
            "user_id": user_id,
        })
        return task

    async def update_task(self, task_id: str, data: TaskUpdate) -> dict[str, Any]:
        existing = await self.task_repo.find_by_id(task_id)
        if not existing:
            raise TaskNotFoundException(task_id)

        if existing.get("status") != TaskStatus.PENDING:
            raise ValidationException("Only pending tasks can be updated.")

        now = datetime.now(timezone.utc)
        if existing.get("scheduled_start") and existing["scheduled_start"] <= now:
            raise ValidationException("Cannot update a task whose scheduled time has passed.")

        update = data.model_dump(exclude_unset=True)
        if "recurrence" in update and update["recurrence"]:
            update["recurrence"] = data.recurrence.model_dump()
        if "verification" in update and update["verification"]:
            update["verification"] = data.verification.model_dump()
        if "category" in update:
            update["category"] = update["category"].value if update["category"] else None

        # Convert incoming datetimes to UTC for storage
        if "scheduled_start" in update and update["scheduled_start"] is not None:
            update["scheduled_start"] = update["scheduled_start"].astimezone(timezone.utc)
        if "scheduled_end" in update and update["scheduled_end"] is not None:
            update["scheduled_end"] = update["scheduled_end"].astimezone(timezone.utc)

        new_start = update.get("scheduled_start", existing["scheduled_start"])
        new_end = update.get("scheduled_end", existing["scheduled_end"])

        if "scheduled_start" in update or "scheduled_end" in update:
            conflicting = await self.task_repo.find_conflicting_task(
                new_start, new_end, exclude_id=task_id
            )
            if conflicting:
                raise ValidationException(
                    f"Time conflict with existing task '{conflicting['title']}'. "
                    f"A 1-minute gap is required between tasks."
                )

        task = await self.task_repo.update_one(task_id, update)
        logger.info("Task updated: %s", task_id)
        return task

    async def delete_task(self, task_id: str) -> bool:
        existing = await self.task_repo.find_by_id(task_id)
        if not existing:
            raise TaskNotFoundException(task_id)
        if existing.get("status") == TaskStatus.ACTIVE:
            raise ValidationException("Cannot delete an active task.")
        return await self.task_repo.delete_one(task_id)

    async def list_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        tasks = await self.task_repo.find_by_user(
            user_id, status, category, date_from, date_to, tags, skip, per_page
        )
        total = await self.task_repo.count_by_user(
            user_id, status, category, date_from, date_to, tags
        )
        return tasks, total

    async def get_upcoming(self, user_id: str) -> list[dict[str, Any]]:
        return await self.task_repo.get_upcoming(user_id)

    async def get_active_task(self, user_id: str) -> Optional[dict[str, Any]]:
        # check if any task is currently active for the user
        active = await self.task_repo.get_active_task(user_id)
        
        if active:
            now = datetime.now(timezone.utc)
            if active.get("scheduled_end") and active["scheduled_end"] <= now:
                await self.mark_task_overdue(active["id"], user_id)
            else:
                return active
            
        next_task = await self.task_repo.get_next_pending_task(user_id)
        if next_task:
            return await self.start_task(next_task["id"], user_id)
        
        return None

    async def start_task(self, task_id: str, user_id: str) -> dict[str, Any]:
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        
        if task.get("status") == TaskStatus.COMPLETED:
            raise ValidationException("Cannot change status of a completed task.")

        # Check no other task is active
        active = await self.task_repo.get_active_task(user_id)
        if active:
            raise TaskAlreadyActiveException(active["id"])

        updated = await self.task_repo.update_one(task_id, {"status": TaskStatus.ACTIVE})
        logger.info("Task started: %s", task_id)

        await self.event_bus.emit(CHANNEL_TASKS, {
            "event_type": "task_started",
            "task_id": task_id,
            "user_id": user_id,
        })
        await self.event_repo.create_event(
            event_type=EventType.TASK_STARTED,
            severity=Severity.INFO,
            user_id=user_id,
            details={"task_id": task_id},
        )
        return updated

    async def complete_task(self, task_id: str, user_id: str) -> dict[str, Any]:
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        
        if task.get("status") == TaskStatus.COMPLETED:
            raise ValidationException("Cannot change status of a completed task.")

        updated = await self.task_repo.update_one(
            task_id, {"status": TaskStatus.COMPLETED}
        )
        logger.info("Task completed: %s", task_id)

        await self.event_bus.emit(CHANNEL_TASKS, {
            "event_type": "task_completed",
            "task_id": task_id,
            "user_id": user_id,
        })
        await self.event_repo.create_event(
            event_type=EventType.TASK_COMPLETED,
            severity=Severity.INFO,
            user_id=user_id,
            details={"task_id": task_id},
        )
        return updated

    async def skip_task(self, task_id: str, user_id: str, reason: str) -> dict[str, Any]:
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        
        if task.get("status") == TaskStatus.COMPLETED:
            raise ValidationException("Cannot change status of a completed task.")

        updated = await self.task_repo.update_one(
            task_id, {"status": TaskStatus.SKIPPED}
        )
        logger.info("Task skipped: %s reason: %s", task_id, reason)
        return updated

    async def mark_task_overdue(self, task_id: str, user_id: str) -> dict[str, Any]:
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        
        if task.get("status") == TaskStatus.COMPLETED:
            raise ValidationException("Cannot change status of a completed task.")

        updated = await self.task_repo.update_one(
            task_id, {"status": TaskStatus.OVERDUE}
        )
        logger.info("Task marked overdue: %s", task_id)

        await self.event_bus.emit(CHANNEL_TASKS, {
            "event_type": "task_overdue",
            "task_id": task_id,
            "user_id": user_id,
        })
        await self.event_repo.create_event(
            event_type=EventType.TASK_OVERDUE,
            severity=Severity.WARNING,
            user_id=user_id,
            details={"task_id": task_id},
        )
        return updated

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        return await self.task_repo.get_user_stats(user_id)
    
    async def get_today_tasks(self, user_id: str) -> list[dict[str, Any]]:
        return await self.task_repo.get_today_tasks(user_id)
