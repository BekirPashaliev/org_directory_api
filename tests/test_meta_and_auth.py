from __future__ import annotations


async def test_health_is_public(client) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_openapi_is_public(client) -> None:
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
    assert "info" in data


async def test_protected_endpoint_requires_api_key(client) -> None:
    r = await client.get("/api/v1/buildings")
    # depending on APIKeyHeader(auto_error=...), missing key can be 401 or 403
    assert r.status_code in (401, 403)


async def test_protected_endpoint_rejects_wrong_api_key(client) -> None:
    r = await client.get("/api/v1/buildings", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


async def test_protected_endpoint_accepts_valid_api_key(client, auth_headers) -> None:
    r = await client.get("/api/v1/buildings", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
