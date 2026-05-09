import pytest


@pytest.mark.asyncio
async def test_add_proxies(client):
    response = await client.post("/proxies", json={
        "proxies": [
            "http://example.com/px-101",
            "http://example.com/px-102",
        ],
        "replace": False,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] == 2
    assert len(data["proxies"]) == 2
    assert data["proxies"][0]["id"] == "px-101"
    assert data["proxies"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_add_proxies_replace(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/old-proxy"],
        "replace": False,
    })

    response = await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
        "replace": True,
    })
    assert response.status_code == 201

    list_resp = await client.get("/proxies")
    data = list_resp.json()
    assert data["total"] == 1
    assert data["proxies"][0]["id"] == "px-101"


@pytest.mark.asyncio
async def test_list_proxies(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
    })
    response = await client.get("/proxies")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["up"] == 0
    assert data["down"] == 0
    assert "failure_rate" in data
    assert len(data["proxies"]) == 1
    assert data["proxies"][0]["id"] == "px-101"
    assert data["proxies"][0]["url"] == "http://example.com/px-101"
    assert "status" in data["proxies"][0]
    assert "last_checked_at" in data["proxies"][0]
    assert "consecutive_failures" in data["proxies"][0]


@pytest.mark.asyncio
async def test_get_proxy_by_id(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
    })
    response = await client.get("/proxies/px-101")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "px-101"
    assert data["url"] == "http://example.com/px-101"
    assert "uptime_percentage" in data
    assert "history" in data
    assert "last_checked_at" in data
    assert "consecutive_failures" in data
    assert "total_checks" in data


@pytest.mark.asyncio
async def test_get_proxy_not_found(client):
    response = await client.get("/proxies/unknown")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_proxy_history(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
    })
    response = await client.get("/proxies/px-101/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    response2 = await client.get("/proxies/unknown/history")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_delete_proxies(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
    })
    response = await client.delete("/proxies")
    assert response.status_code == 204
    assert response.content == b""

    list_resp = await client.get("/proxies")
    data = list_resp.json()
    assert data["total"] == 0
    assert data["proxies"] == []


@pytest.mark.asyncio
async def test_delete_proxies_preserves_alerts(client):
    await client.post("/proxies", json={
        "proxies": ["http://example.com/px-101"],
    })
    await client.delete("/proxies")
    response = await client.get("/alerts")
    assert response.status_code == 200
