"""MongoDB and Redis connection management."""

from __future__ import annotations

import logging
from typing import Optional

import pymongo
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from server.app.core.config import get_settings
from server.app.models.database.collections import INDEXES

logger = logging.getLogger("aegis.database")


class Database:
    """Singleton-style holder for database clients."""

    _mongo_client: Optional[AsyncIOMotorClient] = None
    _mongo_db: Optional[AsyncIOMotorDatabase] = None
    _redis_client: Optional[aioredis.Redis] = None

    @classmethod
    async def connect(cls) -> None:
        settings = get_settings()

        # MongoDB
        cls._mongo_client = AsyncIOMotorClient(
            settings.mongodb.uri,
            maxPoolSize=settings.mongodb.max_pool_size,
        )
        cls._mongo_db = cls._mongo_client[settings.mongodb.database]
        logger.info("Connected to MongoDB: %s", settings.mongodb.database)

        # Create indexes
        await cls._ensure_indexes()

        # Redis
        cls._redis_client = aioredis.from_url(
            settings.redis.uri,
            decode_responses=True,
        )
        await cls._redis_client.ping()
        logger.info("Connected to Redis")

    @classmethod
    async def disconnect(cls) -> None:
        if cls._mongo_client:
            cls._mongo_client.close()
            logger.info("Disconnected from MongoDB")
        if cls._redis_client:
            await cls._redis_client.close()
            logger.info("Disconnected from Redis")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls._mongo_db is None:
            raise RuntimeError("Database not connected. Call Database.connect() first.")
        return cls._mongo_db

    @classmethod
    def get_redis(cls) -> aioredis.Redis:
        if cls._redis_client is None:
            raise RuntimeError("Redis not connected. Call Database.connect() first.")
        return cls._redis_client

    @classmethod
    async def _ensure_indexes(cls) -> None:
        db = cls.get_db()
        for collection_name, keys, kwargs in INDEXES:
            collection = db[collection_name]
            try:
                await collection.create_index(keys, **kwargs)
                logger.debug("Ensured index on %s: %s", collection_name, keys)
            except Exception as e:
                logger.warning("Failed to create index on %s: %s", collection_name, e)

    @classmethod
    async def check_health(cls) -> dict[str, str]:
        """Return health status of database connections."""
        result = {}
        try:
            if cls._mongo_client:
                await cls._mongo_client.admin.command("ping")
                result["mongodb"] = "healthy"
            else:
                result["mongodb"] = "not_connected"
        except Exception:
            result["mongodb"] = "down"

        try:
            if cls._redis_client:
                await cls._redis_client.ping()
                result["redis"] = "healthy"
            else:
                result["redis"] = "not_connected"
        except Exception:
            result["redis"] = "down"

        return result
