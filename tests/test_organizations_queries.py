from __future__ import annotations


async def test_organizations_by_building_kazan(client, auth_headers) -> None:
    rb = await client.get("/api/v1/buildings", headers=auth_headers)
    buildings = rb.json()
    kazan = next(b for b in buildings if "Казань" in b["address"])

    r = await client.get(f"/api/v1/organizations/by-building/{kazan['id']}", headers=auth_headers)
    assert r.status_code == 200
    orgs = r.json()
    names = {o["name"] for o in orgs}
    assert 'ООО "Авто-Лайн"' in names
    assert 'ООО "Запчасти плюс"' in names


async def test_search_organizations_returns_matches(client, auth_headers) -> None:
    r = await client.get("/api/v1/organizations/search", params={"q": "Авто"}, headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert any("Авто" in o["name"] for o in items)


async def test_search_organizations_limit_is_applied(client, auth_headers) -> None:
    r = await client.get("/api/v1/organizations/search", params={"q": "ООО", "limit": 1}, headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1


def _find_activity_id(tree: list[dict], name: str) -> int:
    stack = list(tree)
    while stack:
        node = stack.pop()
        if node["name"] == name:
            return node["id"]
        stack.extend(node.get("children") or [])
    raise AssertionError(f"Activity {name!r} not found in tree")


async def test_orgs_by_activity_include_descendants_behavior(client, auth_headers) -> None:
    rt = await client.get("/api/v1/activities/tree", headers=auth_headers)
    assert rt.status_code == 200
    tree = rt.json()

    food_id = _find_activity_id(tree, "Еда")

    r_all = await client.get(f"/api/v1/organizations/by-activity/{food_id}", headers=auth_headers)
    assert r_all.status_code == 200
    all_orgs = r_all.json()
    assert len(all_orgs) == 4  # seeded: 4 orgs under food subtree

    r_direct = await client.get(
        f"/api/v1/organizations/by-activity/{food_id}",
        params={"include_descendants": False},
        headers=auth_headers,
    )
    assert r_direct.status_code == 200
    direct_orgs = r_direct.json()
    assert len(direct_orgs) == 1  # only org directly tagged with "Еда"