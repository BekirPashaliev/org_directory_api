from __future__ import annotations


async def test_geo_radius_requires_radius_m(client, auth_headers) -> None:
    r = await client.get(
        "/api/v1/organizations/geo",
        params={"mode": "radius", "lat": 55.7558, "lon": 37.6176},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_geo_radius_moscow_returns_distance_sorted(client, auth_headers) -> None:
    r = await client.get(
        "/api/v1/organizations/geo",
        params={"mode": "radius", "lat": 55.7558, "lon": 37.6176, "radius_m": 50},
        headers=auth_headers,
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert all("distance_m" in o for o in items)

    dists = [o["distance_m"] for o in items]
    assert dists == sorted(dists)
    assert all(o["building"]["address"].startswith("Москва") or "Москва" in o["building"]["address"] for o in items)


async def test_geo_bbox_requires_all_params(client, auth_headers) -> None:
    r = await client.get(
        "/api/v1/organizations/geo",
        params={"mode": "bbox", "min_lat": 55.7, "max_lat": 55.9},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_geo_bbox_kazan_returns_two(client, auth_headers) -> None:
    r = await client.get(
        "/api/v1/organizations/geo",
        params={"mode": "bbox", "min_lat": 55.7, "max_lat": 55.9, "min_lon": 49.0, "max_lon": 49.2},
        headers=auth_headers,
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert all("Казань" in o["building"]["address"] for o in items)
    assert all(o["distance_m"] is None for o in items)