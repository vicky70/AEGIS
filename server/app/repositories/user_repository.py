from __future__ import annotations

from typing import Any, Optional

from server.app.models.database.collections import USERS
from server.app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    collection_name = USERS

    async def find_by_username(self, username: str) -> Optional[dict[str, Any]]:
        return await self.find_one({"username": username})

    async def find_by_email(self, email: str) -> Optional[dict[str, Any]]:
        return await self.find_one({"email": email})

    async def update_state(self, user_id: str, state: dict[str, Any]) -> Optional[dict[str, Any]]:
        update = {f"current_state.{k}": v for k, v in state.items()}
        result = await self.collection.find_one_and_update(
            {"_id": self._object_id(user_id)},
            {"$set": update},
            return_document=True,
        )
        return self._to_id(result) if result else None

    async def update_settings(self, user_id: str, settings: dict[str, Any]) -> Optional[dict[str, Any]]:
        update = {f"settings.{k}": v for k, v in settings.items()}
        result = await self.collection.find_one_and_update(
            {"_id": self._object_id(user_id)},
            {"$set": update},
            return_document=True,
        )
        return self._to_id(result) if result else None
