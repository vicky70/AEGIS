from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from server.app.models.database.collections import ACTIVITY_LOGS
from server.app.repositories.base import BaseRepository


class ActivityLogRepository(BaseRepository):
    collection_name = ACTIVITY_LOGS

    async def find_by_task(self, task_id: str) -> list[dict[str, Any]]:
        return await self.find_many(
            filter_={"task_id": task_id},
            sort=[("session_start", -1)],
            limit=100,
        )

    async def find_recent(
        self,
        skip: int = 0,
        limit: int = 20,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        filter_: dict[str, Any] = {}
        if date_from or date_to:
            filter_["session_start"] = {}
            if date_from:
                filter_["session_start"]["$gte"] = date_from
            if date_to:
                filter_["session_start"]["$lte"] = date_to
        return await self.find_many(
            filter_=filter_,
            sort=[("session_start", -1)],
            skip=skip,
            limit=limit,
        )

    async def count_sessions(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        filter_: dict[str, Any] = {}
        if date_from or date_to:
            filter_["session_start"] = {}
            if date_from:
                filter_["session_start"]["$gte"] = date_from
            if date_to:
                filter_["session_start"]["$lte"] = date_to
        return await self.count(filter_)
