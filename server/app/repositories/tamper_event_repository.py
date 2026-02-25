from __future__ import annotations

from typing import Any, Optional

from server.app.models.database.collections import TAMPER_EVENTS
from server.app.repositories.base import BaseRepository


class TamperEventRepository(BaseRepository):
    collection_name = TAMPER_EVENTS

    async def find_recent(
        self,
        event_type: Optional[str] = None,
        classified_as: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filter_: dict[str, Any] = {}
        if event_type:
            filter_["event_type"] = event_type
        if classified_as:
            filter_["classified_as"] = classified_as
        return await self.find_many(
            filter_=filter_,
            sort=[("timestamp", -1)],
            skip=skip,
            limit=limit,
        )

    async def count_events(
        self,
        event_type: Optional[str] = None,
        classified_as: Optional[str] = None,
    ) -> int:
        filter_: dict[str, Any] = {}
        if event_type:
            filter_["event_type"] = event_type
        if classified_as:
            filter_["classified_as"] = classified_as
        return await self.count(filter_)
