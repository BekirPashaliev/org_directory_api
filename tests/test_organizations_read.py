from __future__ import annotations


async def test_read_organization_includes_nested_objects(client, auth_headers) -> None:
    r = await client.get("/api/v1/organizations/search", params={"q": "Молочный мир"}, headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    org_id = items[0]["id"]

    r2 = await client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
    assert r2.status_code == 200
    org = r2.json()

    assert "building" in org and isinstance(org["building"], dict)
    assert "phones" in org and isinstance(org["phones"], list)
    assert "activities" in org and isinstance(org["activities"], list)

    b = org["building"]
    assert set(b.keys()) == {"id", "address", "latitude", "longitude"}
    assert isinstance(b["id"], int)
    assert isinstance(b["address"], str)

    if org["phones"]:
        assert "phone" in org["phones"][0]


async def test_read_organization_not_found(client, auth_headers) -> None:
    r = await client.get("/api/v1/organizations/999999", headers=auth_headers)
    assert r.status_code == 404