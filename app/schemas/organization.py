from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.activity import ActivityOut
from app.schemas.building import BuildingOut


class PhoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    building: BuildingOut
    phones: list[PhoneOut] = Field(default_factory=list)
    activities: list[ActivityOut] = Field(default_factory=list)


class OrganizationOutWithDistance(OrganizationOut):
    distance_m: float | None = None
