from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest


DEFAULT_TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/org_directory_test"
DEFAULT_TEST_API_KEY = "test-key"

# Be robust to pytest's different import modes (e.g. --import-mode=importlib)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _normalize_pg_url(database_url: str) -> str:
    # asyncpg understands "postgresql://", but not "postgresql+asyncpg://"
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _project_root() -> Path:
    return PROJECT_ROOT


async def _recreate_test_database(database_url: str) -> None:
    dsn = _normalize_pg_url(database_url)
    parsed = urlparse(dsn)
    dbname = parsed.path.lstrip("/")

    if "test" not in dbname.lower():
        raise RuntimeError(
            f"Refusing to recreate non-test database '{dbname}'. "
            f"Set DATABASE_URL to a dedicated test DB (e.g. org_directory_test)."
        )
    if not re.fullmatch(r"[A-Za-z0-9_]+", dbname):
        raise RuntimeError(f"Unsafe database name: {dbname!r}")

    admin_parsed = parsed._replace(path="/postgres")
    admin_dsn = urlunparse(admin_parsed)

    conn = await asyncpg.connect(admin_dsn)
    try:
        # FORCE is supported in PG13+, but on older versions it may fail.
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE);')
        except Exception:
            await conn.execute(f'DROP DATABASE IF EXISTS "{dbname}";')
        await conn.execute(f'CREATE DATABASE "{dbname}";')
    finally:
        await conn.close()


def _alembic_upgrade_head(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(_project_root() / "alembic.ini"))
    command.upgrade(cfg, "head")


async def _seed_demo_data() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.db.seed import seed_demo_data

    await seed_demo_data()


@pytest.fixture(scope="session", autouse=True)
def _prepare_db() -> None:
    os.environ.setdefault("API_KEY", DEFAULT_TEST_API_KEY)
    # чтобы сидинг был только в тестовой фикстуре (и не дублировался на startup app)
    os.environ.setdefault("SEED_DATA", "false")

    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("TEST_DATABASE_URL")
        or DEFAULT_TEST_DB_URL
    )
    os.environ["DATABASE_URL"] = database_url

    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        asyncio.run(_recreate_test_database(database_url))
    except Exception as e:
        pytest.skip(f"Postgres is not available for tests: {e}")

    _alembic_upgrade_head(database_url)

    asyncio.run(_seed_demo_data())

    yield



@pytest.fixture()
def app():
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    return create_app()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", DEFAULT_TEST_API_KEY)}


@pytest.fixture()
async def client(app) -> AsyncIterator["httpx.AsyncClient"]:
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
async def db_session() -> AsyncIterator["AsyncSession"]:
    from app.db.session import get_sessionmaker
    async_session = get_sessionmaker()
    async with async_session() as session:  # type: ignore[assignment]
        yield session
