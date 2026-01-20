from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.building import BuildingOut
from app.services.organizations import list_buildings


router = APIRouter(prefix="/buildings")


@router.get("", response_model=list[BuildingOut])
async def get_buildings(session: SessionDep) -> list[BuildingOut]:
    """List all buildings."""

    buildings = await list_buildings(session)
    return [BuildingOut.model_validate(b) for b in buildings]
