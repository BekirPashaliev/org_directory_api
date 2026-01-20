from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.schemas.organization import OrganizationOut, OrganizationOutWithDistance
from app.services.organizations import (
    get_organization,
    list_organizations_by_activity,
    list_organizations_by_building,
    list_organizations_by_geo,
    search_organizations_by_name,
)


router = APIRouter(prefix="/organizations")


@router.get("/by-building/{building_id}", response_model=list[OrganizationOut])
async def organizations_by_building(building_id: int, session: SessionDep) -> list[OrganizationOut]:
    """List organizations in a specific building."""

    orgs = await list_organizations_by_building(session, building_id=building_id)
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.get("/by-activity/{activity_id}", response_model=list[OrganizationOut])
async def organizations_by_activity(
    activity_id: int,
    session: SessionDep,
    include_descendants: bool = Query(default=True, description="Include all nested activities (subtree search)"),
) -> list[OrganizationOut]:
    """List organizations for a given activity."""

    orgs = await list_organizations_by_activity(session, activity_id=activity_id, include_descendants=include_descendants)
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.get("/search", response_model=list[OrganizationOut])
async def search_organizations(
    session: SessionDep,
    q: str = Query(min_length=1, description="Search by organization name (ILIKE %q%)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OrganizationOut]:
    """Search organizations by name."""

    orgs = await search_organizations_by_name(session, q=q, limit=limit)
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.get("/geo", response_model=list[OrganizationOutWithDistance])
async def organizations_geo(
    session: SessionDep,
    mode: Literal["radius", "bbox"] = Query(description="Search mode: radius or bbox"),
    lat: float | None = Query(default=None, description="Reference latitude (mode=radius)"),
    lon: float | None = Query(default=None, description="Reference longitude (mode=radius)"),
    radius_m: float | None = Query(default=None, gt=0, description="Radius in meters (mode=radius)"),
    min_lat: float | None = Query(default=None, description="BBox min latitude (mode=bbox)"),
    max_lat: float | None = Query(default=None, description="BBox max latitude (mode=bbox)"),
    min_lon: float | None = Query(default=None, description="BBox min longitude (mode=bbox)"),
    max_lon: float | None = Query(default=None, description="BBox max longitude (mode=bbox)"),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[OrganizationOutWithDistance]:
    """Search organizations in a given radius or bounding box around the point."""

    try:
        rows = await list_organizations_by_geo(
            session,
            mode=mode,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    out: list[OrganizationOutWithDistance] = []
    for org, dist in rows:
        out.append(OrganizationOutWithDistance.model_validate(org).model_copy(update={"distance_m": dist}))
    return out

@router.get("/{org_id}", response_model=OrganizationOut)
async def read_organization(org_id: int, session: SessionDep) -> OrganizationOut:
    """Get a single organization by id (includes building, phones, activities)."""

    org = await get_organization(session, org_id=org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationOut.model_validate(org)