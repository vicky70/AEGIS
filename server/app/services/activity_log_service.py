from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from server.app.core.exceptions import ResourceNotFoundException
from server.app.models.schemas.activity_log_schemas import ActivitySessionCreate
from server.app.repositories.activity_log_repository import ActivityLogRepository

logger = logging.getLogger("aegis.services.activity_log")


class ActivityLogService:
    def __init__(self, repo: ActivityLogRepository | None = None):
        self.repo = repo or ActivityLogRepository()

    async def submit_session(self, data: ActivitySessionCreate) -> dict[str, Any]:
        doc = data.model_dump()
        session_id = await self.repo.insert_one(doc)
        session = await self.repo.find_by_id(session_id)
        logger.info(
            "Activity session recorded: task=%s duration=%ds",
            data.task_id,
            data.duration_seconds,
        )
        return session

    async def get_session(self, session_id: str) -> dict[str, Any]:
        session = await self.repo.find_by_id(session_id)
        if not session:
            raise ResourceNotFoundException("ActivitySession", session_id)
        return session

    async def get_sessions(
        self,
        task_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        if task_id:
            sessions = await self.repo.find_by_task(task_id)
            return sessions[:per_page], len(sessions)
        sessions = await self.repo.find_recent(skip, per_page, date_from, date_to)
        total = await self.repo.count_sessions(date_from, date_to)
        return sessions, total
