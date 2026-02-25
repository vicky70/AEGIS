from __future__ import annotations

import logging
from typing import Any, Optional

from server.app.core.constants import CHANNEL_INTEGRITY
from server.app.core.exceptions import ResourceNotFoundException
from server.app.models.schemas.behavioral_event_schemas import BehavioralEventCreate
from server.app.repositories.behavioral_event_repository import (
    BehavioralEventRepository,
)
from server.app.services.event_bus import EventBus

logger = logging.getLogger("aegis.services.behavioral_event")


class BehavioralEventService:
    def __init__(self, repo: BehavioralEventRepository | None = None):
        self.repo = repo or BehavioralEventRepository()
        self.event_bus = EventBus.get()

    async def report_event(self, data: BehavioralEventCreate) -> dict[str, Any]:
        doc = data.model_dump()
        event_id = await self.repo.insert_one(doc)
        event = await self.repo.find_by_id(event_id)
        logger.info(
            "Behavioral event recorded: type=%s attempted_by=%s",
            data.event_type,
            data.attempted_by,
        )
        await self.event_bus.emit(CHANNEL_INTEGRITY, {
            "event_type": "behavioral_event",
            "behavioral_event_type": data.event_type,
            "attempted_by": data.attempted_by,
            "component_id": data.component_id,
        })
        return event

    async def get_event(self, event_id: str) -> dict[str, Any]:
        event = await self.repo.find_by_id(event_id)
        if not event:
            raise ResourceNotFoundException("BehavioralEvent", event_id)
        return event

    async def get_events(
        self,
        event_type: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        if task_id:
            events = await self.repo.find_by_task(task_id)
            return events[:per_page], len(events)
        events = await self.repo.find_recent(event_type, skip, per_page)
        total = await self.repo.count_events(event_type)
        return events, total
