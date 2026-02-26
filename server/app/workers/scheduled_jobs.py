"""Background worker: runs periodic scheduled jobs.

- Activate due tasks
- Clear expired penalties
- Delete expired evidence
"""

from __future__ import annotations

import asyncio
import logging

from server.app.core.constants import TaskStatus
from server.app.repositories.evidence_repository import EvidenceRepository
from server.app.repositories.task_repository import TaskRepository
from server.app.services.maintenance_service import MaintenanceService
from server.app.services.penalty_service import PenaltyService
from server.app.services.scheduler_service import SchedulerService

logger = logging.getLogger("aegis.workers.scheduler")

SCHEDULER_INTERVAL_SECONDS = 30


async def scheduled_jobs_loop() -> None:
    """Run periodic maintenance jobs."""
    scheduler = SchedulerService()
    penalty_service = PenaltyService()
    evidence_repo = EvidenceRepository()
    maintenance_service = MaintenanceService()
    task_repo = TaskRepository()

    logger.info("Scheduled jobs worker started (interval=%ds)", SCHEDULER_INTERVAL_SECONDS)

    while True:
        try:
            # 1. Activate tasks whose scheduled_start has passed
            activated = await scheduler.activate_due_tasks()
            if activated:
                logger.info("Auto-activated %d tasks", activated)

            # 2. Clear expired penalties
            cleared = await penalty_service.clear_expired_penalties()
            if cleared:
                logger.info("Cleared %d expired penalties", cleared)

            # 3. Delete expired evidence
            deleted = await evidence_repo.delete_expired()
            if deleted:
                logger.info("Deleted %d expired evidence records", deleted)

            # 4. Expire stale maintenance windows
            expired = await maintenance_service.expire_stale_windows()
            if expired:
                logger.info("Expired %d stale maintenance windows", expired)

            # 5. Mark active tasks past their scheduled_end as overdue
            overdue_tasks = await task_repo.get_overdue_active_tasks()
            for task in overdue_tasks:
                await task_repo.update_one(
                    str(task["_id"]),
                    {"status": TaskStatus.OVERDUE},
                )
            if overdue_tasks:
                logger.info("Marked %d tasks as overdue", len(overdue_tasks))

        except Exception:
            logger.exception("Error in scheduled jobs loop")

        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
