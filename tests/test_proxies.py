import pytest


@pytest.mark.asyncio
async def test_add_proxies(client):
    response = await client.post("/proxies", json={
        "urls": [
            "http://example.com/px-101",
            "http://example.com/px-102",
        ],
        "replace": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 2
    assert data["replaced"] is False


@pytest.mark.asyncio
async def test_add_proxies_replace(client):
    await client.post("/proxies", json={
        "urls": ["http://example.com/old-proxy"],
        "replace": False,
    })

    response = await client.post("/proxies", json={
        "urls": ["http://example.com/px-101"],
        "replace": True,
    })
    assert response.status_code == 200

    list_resp = await client.get("/proxies")
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "px-101"


@pytest.mark.asyncio
async def test_list_proxies(client):
    await client.post("/proxies", json={
        "urls": ["http://example.com/px-101"],
    })
    response = await client.get("/proxies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "px-101"
    assert data[0]["url"] == "http://example.com/px-101"
    assert "status" in data[0]


@pytest.mark.asyncio
async def test_get_proxy_by_id(client):
    await client.post("/proxies", json={
        "urls": ["http://example.com/px-101"],
    })
    response = await client.get("/proxies/px-101")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "px-101"
    assert data["url"] == "http://example.com/px-101"
    assert "uptime_percentage" in data
    assert "history" in data


@pytest.mark.asyncio
async def test_get_proxy_not_found(client):
    response = await client.get("/proxies/unknown")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_proxies(client):
    await client.post("/proxies", json={
        "urls": ["http://example.com/px-101"],
    })
    response = await client.delete("/proxies")
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    list_resp = await client.get("/proxies")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_proxies_preserves_alerts(client):
    await client.post("/proxies", json={
        "urls": ["http://example.com/px-101"],
    })
    await client.delete("/proxies")
    response = await client.get("/alerts")
    assert response.status_code == 200
