from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "Org Directory API"
    api_v1_prefix: str = "/api/v1"

    # Auth
    api_key: str = "change-me"

    # DB
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/org_directory"

    # When true, inserts demo data (idempotent) on app startup.
    seed_data: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
