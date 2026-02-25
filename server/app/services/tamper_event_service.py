from __future__ import annotations

import logging
from typing import Any, Optional

from server.app.core.constants import CHANNEL_INTEGRITY
from server.app.core.exceptions import ResourceNotFoundException
from server.app.models.schemas.tamper_event_schemas import TamperEventCreate
from server.app.repositories.tamper_event_repository import TamperEventRepository
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.tamper_event")


class TamperEventService:
    def __init__(self, repo: TamperEventRepository | None = None):
        self.repo = repo or TamperEventRepository()
        self.event_bus = EventBus.get()

    async def report_event(self, data: TamperEventCreate) -> dict[str, Any]:
        doc = data.model_dump()
        event_id = await self.repo.insert_one(doc)
        event = await self.repo.find_by_id(event_id)
        logger.info(
            "Tamper event recorded: type=%s classified=%s",
            data.event_type,
            data.classified_as,
        )
        await self.event_bus.emit(CHANNEL_INTEGRITY, {
            "event_type": "tamper_event",
            "tamper_event_type": data.event_type,
            "classified_as": data.classified_as,
            "component_id": data.component_id,
        })
        return event

    async def get_event(self, event_id: str) -> dict[str, Any]:
        event = await self.repo.find_by_id(event_id)
        if not event:
            raise ResourceNotFoundException("TamperEvent", event_id)
        return event

    async def get_events(
        self,
        event_type: Optional[str] = None,
        classified_as: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        events = await self.repo.find_recent(event_type, classified_as, skip, per_page)
        total = await self.repo.count_events(event_type, classified_as)
        return events, total
