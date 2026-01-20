from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Activity
from app.schemas.activity import ActivityTreeNode


async def get_descendant_activity_ids(
    session: AsyncSession, activity_id: int, include_self: bool = True
) -> list[int]:
    """Returns IDs of the activity subtree (recursive CTE)."""

    # Recursive CTE: start node
    cte = select(Activity.id).where(Activity.id == activity_id).cte(recursive=True, name="activity_tree")
    # Recursive member: children
    cte = cte.union_all(
        select(Activity.id).where(Activity.parent_id == cte.c.id)
    )

    stmt = select(cte.c.id)
    res = await session.execute(stmt)
    ids = [int(row[0]) for row in res.fetchall()]

    if not include_self:
        ids = [i for i in ids if i != activity_id]
    return ids


async def list_activity_tree(session: AsyncSession) -> list[ActivityTreeNode]:
    """Returns activity tree limited to 3 levels."""

    stmt = select(Activity).order_by(Activity.level, Activity.id)
    res = await session.execute(stmt)
    rows: list[Activity] = list(res.scalars().all())

    # Index by parent
    children_map: dict[int | None, list[Activity]] = defaultdict(list)
    for a in rows:
        children_map[a.parent_id].append(a)

    def build(parent_id: int | None, *, max_level: int = 3) -> list[ActivityTreeNode]:
        nodes: list[ActivityTreeNode] = []
        for a in children_map.get(parent_id, []):
            node = ActivityTreeNode(id=a.id, name=a.name, level=int(a.level), children=[])
            if int(a.level) < max_level:
                node.children = build(a.id, max_level=max_level)
            nodes.append(node)
        return nodes

    return build(None, max_level=3)
