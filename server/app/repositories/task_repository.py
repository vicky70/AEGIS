from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId

from server.app.core.constants import TaskStatus
from server.app.models.database.collections import TASKS
from server.app.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    collection_name = TASKS

    async def find_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filter_: dict[str, Any] = {"user_id": user_id}
        if status:
            filter_["status"] = status
        if category:
            filter_["category"] = category
        if date_from or date_to:
            filter_["scheduled_start"] = {}
            if date_from:
                filter_["scheduled_start"]["$gte"] = date_from
            if date_to:
                filter_["scheduled_start"]["$lte"] = date_to
        if tags:
            filter_["tags"] = {"$all": tags}
        return await self.find_many(
            filter_=filter_,
            sort=[("scheduled_start", 1)],
            skip=skip,
            limit=limit,
        )

    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
    ) -> int:
        filter_: dict[str, Any] = {"user_id": user_id}
        if status:
            filter_["status"] = status
        if category:
            filter_["category"] = category
        if date_from or date_to:
            filter_["scheduled_start"] = {}
            if date_from:
                filter_["scheduled_start"]["$gte"] = date_from
            if date_to:
                filter_["scheduled_start"]["$lte"] = date_to
        if tags:
            filter_["tags"] = {"$all": tags}
        return await self.count(filter_)

    async def get_upcoming(self, user_id: str, hours: int = 24) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return await self.find_many(
            filter_={
                "user_id": user_id,
                "status": {"$in": [TaskStatus.PENDING, TaskStatus.ACTIVE]},
                "scheduled_start": {"$gte": now, "$lte": now + timedelta(hours=hours)},
            },
            sort=[("scheduled_start", 1)],
            limit=50,
        )

    async def get_active_task(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self.find_one(
            {"user_id": user_id, "status": TaskStatus.ACTIVE}
        )

    async def get_tasks_due_for_activation(self) -> list[dict[str, Any]]:
        """Find pending tasks whose scheduled_start has passed."""
        now = datetime.now(timezone.utc)
        return await self.find_many(
            filter_={
                "status": TaskStatus.PENDING,
                "scheduled_start": {"$lte": now},
            },
            sort=[("scheduled_start", 1)],
            limit=100,
        )

    async def get_overdue_active_tasks(self) -> list[dict[str, Any]]:
        """Find active tasks whose scheduled_end has passed."""
        now = datetime.now(timezone.utc)
        return await self.find_many(
            filter_={
                "status": TaskStatus.ACTIVE,
                "scheduled_end": {"$lte": now},
            },
            sort=[("scheduled_end", 1)],
            limit=100,
        )

    async def get_user_stats(self, user_id: str) -> dict[str, int]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        result = {}
        async for doc in self.collection.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        return result

    async def add_evidence_ref(self, task_id: str, evidence_id: str) -> None:
        await self.collection.update_one(
            {"_id": self._object_id(task_id)},
            {"$push": {"completion_evidence": evidence_id}},
        )
