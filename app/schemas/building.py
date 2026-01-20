from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address: str
    latitude: float
    longitude: float
