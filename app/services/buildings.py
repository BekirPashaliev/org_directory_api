from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Building


async def list_buildings(session: AsyncSession) -> list[Building]:
    stmt = select(Building).order_by(Building.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def building_exists(session: AsyncSession, *, building_id: int) -> bool:
    stmt = select(Building.id).where(Building.id == building_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None