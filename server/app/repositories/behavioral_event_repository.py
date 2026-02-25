from __future__ import annotations

from typing import Any, Optional

from server.app.models.database.collections import BEHAVIORAL_EVENTS
from server.app.repositories.base import BaseRepository


class BehavioralEventRepository(BaseRepository):
    collection_name = BEHAVIORAL_EVENTS

    async def find_recent(
        self,
        event_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filter_: dict[str, Any] = {}
        if event_type:
            filter_["event_type"] = event_type
        return await self.find_many(
            filter_=filter_,
            sort=[("timestamp", -1)],
            skip=skip,
            limit=limit,
        )

    async def find_by_task(self, task_id: str) -> list[dict[str, Any]]:
        return await self.find_many(
            filter_={"task_context.task_id": task_id},
            sort=[("timestamp", -1)],
            limit=100,
        )

    async def count_events(
        self,
        event_type: Optional[str] = None,
    ) -> int:
        filter_: dict[str, Any] = {}
        if event_type:
            filter_["event_type"] = event_type
        return await self.count(filter_)
