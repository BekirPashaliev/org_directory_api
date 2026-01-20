from __future__ import annotations

import os
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Create (and cache) the async SQLAlchemy engine.

    Keep it lazy so tests / migrations can set DATABASE_URL before first use.
    """

    settings = get_settings()
    kwargs: dict = {"pool_pre_ping": True}

    # pytest sets PYTEST_CURRENT_TEST; plus a safety-net for DB names containing "test"
    if os.getenv("PYTEST_CURRENT_TEST") or "test" in settings.database_url.lower():
        kwargs["poolclass"] = NullPool

    return create_async_engine(settings.database_url, **kwargs)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_sessionmaker()
    async with async_session() as session:
        yield session

async def dispose_engine() -> None:
    """Dispose engine and clear caches (useful in tests)."""

    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    get_settings.cache_clear()

