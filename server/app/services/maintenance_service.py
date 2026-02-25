from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from server.app.core.constants import MaintenanceWindowStatus
from server.app.core.exceptions import ResourceNotFoundException
from server.app.models.schemas.maintenance_schemas import (
    MaintenanceWindowCreate,
    MaintenanceWindowUpdate,
)
from server.app.repositories.maintenance_window_repository import (
    MaintenanceWindowRepository,
)

logger = logging.getLogger("aegis.services.maintenance")

MAINTENANCE_BUFFER_MINUTES = 10


class MaintenanceService:
    def __init__(self, repo: MaintenanceWindowRepository | None = None):
        self.repo = repo or MaintenanceWindowRepository()

    async def declare_window(self, data: MaintenanceWindowCreate) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(
            minutes=data.expected_duration_minutes + MAINTENANCE_BUFFER_MINUTES
        )
        doc = {
            "declared_at": now,
            "reason": data.reason,
            "expected_duration_minutes": data.expected_duration_minutes,
            "expires_at": expires_at,
            "status": MaintenanceWindowStatus.DECLARED,
            "actual_stop_at": None,
            "actual_resume_at": None,
            "total_downtime_seconds": None,
        }
        window_id = await self.repo.insert_one(doc)
        window = await self.repo.find_by_id(window_id)
        logger.info(
            "Maintenance window declared: reason=%s duration=%dmin expires_at=%s",
            data.reason,
            data.expected_duration_minutes,
            expires_at.isoformat(),
        )
        return window

    async def update_window(
        self, window_id: str, data: MaintenanceWindowUpdate
    ) -> dict[str, Any]:
        window = await self.repo.find_by_id(window_id)
        if not window:
            raise ResourceNotFoundException("MaintenanceWindow", window_id)

        update = data.model_dump(exclude_unset=True)
        updated = await self.repo.update_one(window_id, update)
        logger.info("Maintenance window updated: id=%s fields=%s", window_id, list(update.keys()))
        return updated

    async def get_window(self, window_id: str) -> dict[str, Any]:
        window = await self.repo.find_by_id(window_id)
        if not window:
            raise ResourceNotFoundException("MaintenanceWindow", window_id)
        return window

    async def list_windows(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * per_page
        windows = await self.repo.find_recent(skip, per_page)
        total = await self.repo.count_windows()
        return windows, total

    async def get_active_or_declared(self) -> Optional[dict[str, Any]]:
        return await self.repo.find_active_or_declared()

    async def expire_stale_windows(self) -> int:
        return await self.repo.expire_stale_windows()
