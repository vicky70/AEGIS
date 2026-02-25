"""Base repository with common CRUD operations for MongoDB."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from server.app.models.database.connection import Database


class BaseRepository:
    """Base class providing common MongoDB CRUD operations."""

    collection_name: str = ""

    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or Database.get_db()

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.db[self.collection_name]

    @staticmethod
    def _to_id(doc: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB _id to string id."""
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    @staticmethod
    def _object_id(id_str: str) -> ObjectId:
        return ObjectId(id_str)

    async def find_by_id(self, id_str: str) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one({"_id": self._object_id(id_str)})
        return self._to_id(doc) if doc else None

    async def find_many(
        self,
        filter_: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        cursor = self.collection.find(filter_ or {})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        return [self._to_id(doc) async for doc in cursor]

    async def count(self, filter_: dict[str, Any] | None = None) -> int:
        return await self.collection.count_documents(filter_ or {})

    async def insert_one(self, document: dict[str, Any]) -> str:
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def update_one(
        self, id_str: str, update: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        result = await self.collection.find_one_and_update(
            {"_id": self._object_id(id_str)},
            {"$set": {**update, "updated_at": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return self._to_id(result) if result else None

    async def delete_one(self, id_str: str) -> bool:
        result = await self.collection.delete_one({"_id": self._object_id(id_str)})
        return result.deleted_count > 0

    async def find_one(self, filter_: dict[str, Any]) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one(filter_)
        return self._to_id(doc) if doc else None
