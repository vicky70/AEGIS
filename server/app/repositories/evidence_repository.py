from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from server.app.models.database.collections import EVIDENCE
from server.app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository):
    collection_name = EVIDENCE

    async def find_by_task(self, task_id: str) -> list[dict[str, Any]]:
        return await self.find_many(
            filter_={"task_id": task_id},
            sort=[("captured_at", -1)],
            limit=100,
        )

    async def find_by_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        return await self.find_many(
            filter_={"user_id": user_id},
            sort=[("captured_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.collection.delete_many(
            {"retention_until": {"$lte": now}}
        )
        return result.deleted_count
