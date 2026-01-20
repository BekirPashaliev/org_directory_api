from __future__ import annotations

import math
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.sql import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Building, Organization, organization_activity
from app.services.activities import get_descendant_activity_ids


def _org_base_query() -> Select[tuple[Organization]]:
    return (
        select(Organization)
        .options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities),
        )
    )


async def get_organization(session: AsyncSession, *, org_id: int) -> Organization | None:
    stmt = _org_base_query().where(Organization.id == org_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def list_organizations_by_building(session: AsyncSession, *, building_id: int) -> list[Organization]:
    stmt = _org_base_query().where(Organization.building_id == building_id).order_by(Organization.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def list_organizations_by_activity(
    session: AsyncSession, *, activity_id: int, include_descendants: bool = True
) -> list[Organization]:
    ids = [activity_id]
    if include_descendants:
        ids = await get_descendant_activity_ids(session, activity_id=activity_id, include_self=True)

    stmt = (
        _org_base_query()
        .join(organization_activity, organization_activity.c.organization_id == Organization.id)
        .where(organization_activity.c.activity_id.in_(ids))
        .distinct()
        .order_by(Organization.id)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def search_organizations_by_name(session: AsyncSession, *, q: str, limit: int = 50) -> list[Organization]:
    q_stripped = q.strip()
    if not q_stripped:
        return []
    escaped = _escape_like(q_stripped)
    q_like = f"%{escaped}%"
    stmt = (
        _org_base_query()
        .where(Organization.name.ilike(q_like, escape="\\"))
        .order_by(Organization.name)
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())

def _escape_like(value: str, *, escape: str = "\\") -> str:
    return (
        value.replace(escape, escape + escape)
        .replace("%", escape + "%")
        .replace("_", escape + "_")
    )

async def list_buildings(session: AsyncSession) -> list[Building]:
    stmt = select(Building).order_by(Building.id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


def _haversine_distance_m(
    *,
    lat_deg: float,
    lon_deg: float,
    building_lat_col: ColumnElement[float],
    building_lon_col: ColumnElement[float],
) -> ColumnElement[float]:

    """Returns SQL expression for great-circle distance in meters."""

    # https://en.wikipedia.org/wiki/Haversine_formula
    earth_radius_m = 6371000.0
    lat1 = func.radians(lat_deg)
    lat2 = func.radians(building_lat_col)
    dlat = func.radians(building_lat_col - lat_deg)
    dlon = func.radians(building_lon_col - lon_deg)

    a = func.pow(func.sin(dlat / 2), 2) + func.cos(lat1) * func.cos(lat2) * func.pow(func.sin(dlon / 2), 2)
    c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
    return earth_radius_m * c


async def list_organizations_by_geo(
    session: AsyncSession,
    *,
    mode: Literal["radius", "bbox"],
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    limit: int = 200,
) -> list[tuple[Organization, float | None]]:
    """Returns organizations with optional distance (for radius mode)."""

    # Select only Organization; Building is joined only for geo filtering.
    base = _org_base_query().join(Building, Building.id == Organization.building_id)

    if mode == "radius":
        if lat is None or lon is None:
            raise ValueError("lat and lon must be provided for mode=radius")
        if radius_m is None or radius_m <= 0:
            raise ValueError("radius_m must be provided and > 0 for mode=radius")

        _validate_lat_lon(lat=lat, lon=lon)
        min_lat, max_lat, min_lon, max_lon = _bbox_around(lat=lat, lon=lon, radius_m=radius_m)

        distance = _haversine_distance_m(
            lat_deg=lat,
            lon_deg=lon,
            building_lat_col=Building.latitude,
            building_lon_col=Building.longitude,
        )

        stmt = (
            base.add_columns(distance.label("distance_m"))
            .where(Building.latitude.between(min_lat, max_lat))
            .where(Building.longitude.between(min_lon, max_lon))
            .where(distance <= radius_m)
            .order_by(distance)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return [(org, float(dist)) for org, dist in res.all()]

    if mode == "bbox":
        if min_lat > max_lat:
            raise ValueError("min_lat must be <= max_lat")
        if min_lon > max_lon:
            raise ValueError("min_lon must be <= max_lon")

        _validate_lat_lon(lat=min_lat, lon=min_lon)
        _validate_lat_lon(lat=max_lat, lon=max_lon)

        # Bounding box filter
        if None in (min_lat, max_lat, min_lon, max_lon):
            raise ValueError("min_lat, max_lat, min_lon, max_lon must be provided for mode=bbox")

        stmt = (
            base.where(Building.latitude.between(min_lat, max_lat))
            .where(Building.longitude.between(min_lon, max_lon))
            .order_by(Organization.id)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return [(org, None) for org in res.scalars().all()]

    raise ValueError("Unknown mode")


def _validate_lat_lon(*, lat: float | None, lon: float | None) -> None:
    if lat is None or lon is None:
        raise ValueError("lat/lon must be provided")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError("lat must be between -90 and 90")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("lon must be between -180 and 180")


def _bbox_around(*, lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    deg_per_meter_lat = 1.0 / 111_320.0
    lat_delta = radius_m * deg_per_meter_lat
    lat_rad = math.radians(lat)
    cos_lat = max(0.01, abs(math.cos(lat_rad)))
    deg_per_meter_lon = 1.0 / (111_320.0 * cos_lat)
    lon_delta = radius_m * deg_per_meter_lon
    return (
        max(-90.0, lat - lat_delta),
        min(90.0, lat + lat_delta),
        max(-180.0, lon - lon_delta),
        min(180.0, lon + lon_delta),
    )