"""Application settings, loaded from the environment (and an optional .env file)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Connection string for the target schema (created out-of-band via `make migrate`).
    database_url: str = "postgresql://professional_network:professional_network@localhost:5433/professional_network"

    # asyncpg pool sizing.
    db_pool_min: int = 1
    db_pool_max: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
