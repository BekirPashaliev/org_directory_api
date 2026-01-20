from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    level: int


class ActivityTreeNode(BaseModel):
    """Activity node with up to 3 levels of children."""

    id: int
    name: str
    level: int
    children: list["ActivityTreeNode"] = Field(default_factory=list)
