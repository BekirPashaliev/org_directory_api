#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Waiting for database..."
python - <<'PY'
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

async def main():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    for i in range(60):
        try:
            async with engine.connect() as c:
                from sqlalchemy import text
                await c.execute(text("SELECT 1"))
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        raise SystemExit("DB not ready")
    await engine.dispose()

asyncio.run(main())
PY

echo "[entrypoint] Applying migrations..."
alembic upgrade head

echo "[entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
