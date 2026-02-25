from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from server.app.core.constants import ComponentStatus, Severity
from server.app.models.database.collections import (
    PENALTY_HISTORY,
    SYSTEM_COMPONENTS,
    SYSTEM_EVENTS,
)
from server.app.repositories.base import BaseRepository


class SystemComponentRepository(BaseRepository):
    collection_name = SYSTEM_COMPONENTS

    async def find_by_component_id(self, component_id: str) -> Optional[dict[str, Any]]:
        return await self.find_one({"component_id": component_id})

    async def update_heartbeat(
        self, component_id: str, timestamp: datetime, reported_hash: str
    ) -> Optional[dict[str, Any]]:
        result = await self.collection.find_one_and_update(
            {"component_id": component_id},
            {
                "$set": {
                    "last_heartbeat": timestamp,
                    "last_reported_hash": reported_hash,
                    "status": ComponentStatus.HEALTHY,
                    "consecutive_missed": 0,
                }
            },
            return_document=True,
        )
        return self._to_id(result) if result else None

    async def increment_missed(self, component_id: str) -> Optional[dict[str, Any]]:
        result = await self.collection.find_one_and_update(
            {"component_id": component_id},
            {
                "$inc": {"consecutive_missed": 1},
                "$set": {"status": ComponentStatus.WARNING},
            },
            return_document=True,
        )
        return self._to_id(result) if result else None

    async def set_status(
        self, component_id: str, status: ComponentStatus
    ) -> Optional[dict[str, Any]]:
        result = await self.collection.find_one_and_update(
            {"component_id": component_id},
            {"$set": {"status": status}},
            return_document=True,
        )
        return self._to_id(result) if result else None

    async def get_all_components(self) -> list[dict[str, Any]]:
        return await self.find_many(limit=200)

    async def get_status_counts(self) -> dict[str, int]:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        result = {}
        async for doc in self.collection.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        return result


class SystemEventRepository(BaseRepository):
    collection_name = SYSTEM_EVENTS

    async def get_recent(
        self,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filter_: dict[str, Any] = {}
        if severity:
            filter_["severity"] = severity
        return await self.find_many(
            filter_=filter_,
            sort=[("timestamp", -1)],
            limit=limit,
        )

    async def create_event(
        self,
        event_type: str,
        severity: str,
        component_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> str:
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "component_id": component_id,
            "user_id": user_id,
            "severity": severity,
            "details": details or {},
            "acknowledged": False,
        }
        return await self.insert_one(doc)


class PenaltyRepository(BaseRepository):
    collection_name = PENALTY_HISTORY

    async def get_active_penalty(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.find_one(
            {"user_id": user_id, "ended_at": None}
        )

    async def get_history(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        return await self.find_many(
            filter_={"user_id": user_id},
            sort=[("triggered_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def count_by_user(self, user_id: str) -> int:
        return await self.count({"user_id": user_id})

    async def end_penalty(
        self,
        penalty_id: str,
        early_release: bool = False,
        reason: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        update: dict[str, Any] = {"ended_at": datetime.now(timezone.utc)}
        if early_release:
            update["early_release"] = True
            update["early_release_reason"] = reason
        return await self.update_one(penalty_id, update)

    async def get_expired_penalties(self) -> list[dict[str, Any]]:
        """Find active penalties whose duration has passed."""
        now = datetime.now(timezone.utc)
        pipeline = [
            {"$match": {"ended_at": None}},
            {
                "$addFields": {
                    "expires_at": {
                        "$add": [
                            "$triggered_at",
                            {"$multiply": ["$duration_minutes", 60000]},
                        ]
                    }
                }
            },
            {"$match": {"expires_at": {"$lte": now}}},
        ]
        return [self._to_id(doc) async for doc in self.collection.aggregate(pipeline)]
