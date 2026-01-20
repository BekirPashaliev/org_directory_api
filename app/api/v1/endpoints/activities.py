from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.activity import ActivityTreeNode
from app.services.activities import list_activity_tree


router = APIRouter(prefix="/activities")


@router.get("/tree", response_model=list[ActivityTreeNode])
async def get_activity_tree(session: SessionDep) -> list[ActivityTreeNode]:
    """Get activity tree limited to 3 levels."""

    return await list_activity_tree(session)
