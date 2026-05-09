import pytest


@pytest.mark.asyncio
async def test_update_config(client):
    response = await client.post("/config", json={
        "check_interval_seconds": 10,
        "request_timeout_ms": 3000,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["check_interval_seconds"] == 10
    assert data["request_timeout_ms"] == 3000


@pytest.mark.asyncio
async def test_update_config_partial(client):
    await client.post("/config", json={
        "request_timeout_ms": 3000,
    })
    response = await client.post("/config", json={
        "check_interval_seconds": 15,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["check_interval_seconds"] == 15
    assert data["request_timeout_ms"] == 3000


@pytest.mark.asyncio
async def test_update_config_unknown_fields(client):
    response = await client.post("/config", json={
        "check_interval_seconds": 20,
        "unknown_field": "ignored",
        "another_unknown": 123,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["check_interval_seconds"] == 20
