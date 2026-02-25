from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class ServerSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    debug: bool = False
    cors_origins: list[str] = ["*"]


class MongoDBSettings(BaseSettings):
    uri: str = "mongodb://localhost:27017"
    database: str = "aegis"
    max_pool_size: int = 50

    model_config = {"env_prefix": "MONGODB_"}


class RedisSettings(BaseSettings):
    uri: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": "REDIS_"}


class SecuritySettings(BaseSettings):
    jwt_secret: str = "change-me"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    encryption_key_derivation_salt: str = "change-me"

    model_config = {"env_prefix": ""}


class AegisSettings(BaseSettings):
    heartbeat_interval_seconds: int = 30
    heartbeat_grace_period_seconds: int = 120
    penalty_default_duration_minutes: int = 30
    focus_zone_default_radius_meters: int = 30
    evidence_retention_days: int = 90
    lockdown_auto_trigger: bool = True

    model_config = {"env_prefix": ""}


class Settings(BaseSettings):
    env: str = Field(default="development", alias="AEGIS_ENV")
    host: str = Field(default="127.0.0.1", alias="AEGIS_HOST")
    port: int = Field(default=8000, alias="AEGIS_PORT")
    workers: int = Field(default=1, alias="AEGIS_WORKERS")
    debug: bool = Field(default=False, alias="AEGIS_DEBUG")
    cors_origins: list[str] = ["*"]

    # Sub-settings
    mongodb: MongoDBSettings = MongoDBSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()
    aegis: AegisSettings = AegisSettings()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @classmethod
    def from_yaml(cls, env: str | None = None) -> Settings:
        """Load settings from YAML config file, then overlay env vars."""
        env = env or os.getenv("AEGIS_ENV", "development")
        config_path = CONFIG_DIR / f"{env}.yaml"
        yaml_data: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
        return cls(**yaml_data)


@lru_cache
def get_settings() -> Settings:
    return Settings.from_yaml()
