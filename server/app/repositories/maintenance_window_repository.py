from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from server.app.core.constants import MaintenanceWindowStatus
from server.app.models.database.collections import MAINTENANCE_WINDOWS
from server.app.repositories.base import BaseRepository


class MaintenanceWindowRepository(BaseRepository):
    collection_name = MAINTENANCE_WINDOWS

    async def find_active_or_declared(self) -> Optional[dict[str, Any]]:
        """Find the current maintenance window (declared or active, not expired)."""
        now = datetime.now(timezone.utc)
        return await self.find_one({
            "status": {"$in": [
                MaintenanceWindowStatus.DECLARED,
                MaintenanceWindowStatus.ACTIVE,
            ]},
            "expires_at": {"$gt": now},
        })

    async def find_recent(
        self, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        return await self.find_many(
            sort=[("declared_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def count_windows(self) -> int:
        return await self.count()

    async def expire_stale_windows(self) -> int:
        """Move declared windows past their expires_at to 'expired' status."""
        now = datetime.now(timezone.utc)
        result = await self.collection.update_many(
            {
                "status": MaintenanceWindowStatus.DECLARED,
                "expires_at": {"$lte": now},
            },
            {"$set": {"status": MaintenanceWindowStatus.EXPIRED}},
        )
        return result.modified_count
