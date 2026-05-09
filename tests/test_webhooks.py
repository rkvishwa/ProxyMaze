import pytest


@pytest.mark.asyncio
async def test_register_webhook(client):
    response = await client.post("/webhooks", json={
        "url": "http://example.com/webhook",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["registered"] is True
    assert data["url"] == "http://example.com/webhook"


@pytest.mark.asyncio
async def test_register_webhook_unknown_fields(client):
    response = await client.post("/webhooks", json={
        "url": "http://example.com/webhook",
        "unknown": "ignored",
    })
    assert response.status_code == 200
