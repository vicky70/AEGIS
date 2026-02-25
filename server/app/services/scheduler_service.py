from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from server.app.core.constants import CHANNEL_TASKS, TaskStatus
from server.app.repositories.task_repository import TaskRepository
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.scheduler")


class SchedulerService:
    def __init__(self, task_repo: TaskRepository | None = None):
        self.task_repo = task_repo or TaskRepository()
        self.event_bus = EventBus.get()

    async def activate_due_tasks(self) -> int:
        """Find pending tasks whose scheduled_start has passed and activate them.

        Returns the number of tasks activated.
        """
        tasks = await self.task_repo.get_tasks_due_for_activation()
        activated = 0

        for task in tasks:
            user_id = task["user_id"]
            task_id = task["id"]

            # Check if user already has an active task
            active = await self.task_repo.get_active_task(user_id)
            if active:
                logger.debug(
                    "Skipping activation of %s — user %s has active task %s",
                    task_id,
                    user_id,
                    active["id"],
                )
                continue

            await self.task_repo.update_one(task_id, {"status": TaskStatus.ACTIVE})
            activated += 1
            logger.info("Auto-activated task %s for user %s", task_id, user_id)

            await self.event_bus.emit(CHANNEL_TASKS, {
                "event_type": "task_activated",
                "task_id": task_id,
                "user_id": user_id,
            })

        return activated
