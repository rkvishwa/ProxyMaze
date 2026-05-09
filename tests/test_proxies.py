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
async def test_add_proxies_duplicates(client):
    response = await client.post("/proxies", json={
        "proxies": [
            "http://host1.example.com/px-101",
            "http://host2.example.com/px-101",
            "http://host3.example.com/px-102",
        ],
        "replace": False,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] == 3
    assert len(data["proxies"]) == 3
    assert "rejected" not in data

    list_resp = await client.get("/proxies")
    list_data = list_resp.json()
    assert list_data["total"] == 2


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
async def test_replace_proxies_resolves_active_alert(client):
    import asyncio
    from app.models import Proxy, CheckStatus

    state = client._transport.app.state.app_state

    # Set up pool with all-down proxies to fire an alert
    async with state.lock:
        state.proxies.clear()
        for i in range(5):
            p = Proxy(id=f"px-{i}", url=f"http://example.com/px-{i}")
            p.status = CheckStatus.DOWN
            state.proxies[p.id] = p

    from app.analyzer import calculate_failure_rate
    from app.alert_manager import evaluate_alerts

    await evaluate_alerts(state, calculate_failure_rate(state))
    assert state.active_alert is not None
    first_alert_id = state.active_alert.alert_id

    # Replace pool via HTTP endpoint
    response = await client.post("/proxies", json={
        "proxies": [
            "http://example.com/px-101",
            "http://example.com/px-102",
        ],
        "replace": True,
    })
    assert response.status_code == 201

    assert state.active_alert is None
    assert len(state.alerts) == 1
    assert state.alerts[0].alert_id == first_alert_id
    assert state.alerts[0].status.value == "resolved"
    assert state.alerts[0].resolved_at is not None
