from __future__ import annotations


async def test_list_buildings_returns_expected_shape(client, auth_headers) -> None:
    r = await client.get("/api/v1/buildings", headers=auth_headers)
    assert r.status_code == 200
    buildings = r.json()
    assert len(buildings) == 5
    for b in buildings:
        assert set(b.keys()) == {"id", "address", "latitude", "longitude"}
        assert isinstance(b["id"], int)
        assert isinstance(b["address"], str)


async def test_list_buildings_contains_moscow(client, auth_headers) -> None:
    r = await client.get("/api/v1/buildings", headers=auth_headers)
    buildings = r.json()
    assert any("Москва" in b["address"] for b in buildings)