from __future__ import annotations

import pytest
from sqlalchemy import select


def _max_depth(nodes: list[dict]) -> int:
    def walk(node: dict) -> int:
        children = node.get("children") or []
        if not children:
            return 1
        return 1 + max(walk(c) for c in children)

    return max((walk(n) for n in nodes), default=0)


async def test_activity_tree_roots_and_depth_limit(client, auth_headers) -> None:
    r = await client.get("/api/v1/activities/tree", headers=auth_headers)
    assert r.status_code == 200
    tree = r.json()

    root_names = {n["name"] for n in tree}
    assert {"Еда", "Автомобили"} <= root_names
    assert _max_depth(tree) <= 3


async def test_get_descendants_includes_self(db_session) -> None:
    from app.db.models import Activity
    from app.services.activities import get_descendant_activity_ids

    food_id = await db_session.scalar(select(Activity.id).where(Activity.name == "Еда", Activity.parent_id.is_(None)))
    assert isinstance(food_id, int)

    ids = await get_descendant_activity_ids(db_session, food_id)
    # seeded subtree: Еда + Мясная + Молочная + Сосиски + Сыры
    assert food_id in ids
    assert len(ids) == 5


async def test_activity_db_constraints_depth_and_unique(db_session) -> None:
    """
    Senior-ish тест: проверяем реальные DB-ограничения из миграции:
    - триггер запрещает глубину > 3
    - uq_activity_parent_name запрещает одинаковые имена у одного parent
    """
    from app.db.models import Activity

    # unique constraint within same parent
    parent = Activity(name="__test_parent__")
    db_session.add(parent)
    await db_session.flush()

    db_session.add(Activity(name="__dup__", parent_id=parent.id))
    await db_session.flush()

    db_session.add(Activity(name="__dup__", parent_id=parent.id))
    with pytest.raises(Exception):
        await db_session.flush()
    await db_session.rollback()

    # depth trigger (max 3 levels)
    root = Activity(name="__root__")
    db_session.add(root)
    await db_session.flush()

    child = Activity(name="__child__", parent_id=root.id)
    db_session.add(child)
    await db_session.flush()

    grand = Activity(name="__grand__", parent_id=child.id)
    db_session.add(grand)
    await db_session.flush()

    too_deep = Activity(name="__too_deep__", parent_id=grand.id)
    db_session.add(too_deep)
    with pytest.raises(Exception) as exc:
        await db_session.flush()

    assert "depth" in str(exc.value).lower() or "limit" in str(exc.value).lower()
    await db_session.rollback()