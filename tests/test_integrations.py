import pytest


@pytest.mark.asyncio
async def test_register_slack_integration(client):
    response = await client.post("/integrations", json={
        "type": "slack",
        "webhook_url": "https://hooks.slack.com/services/TEST",
        "username": "ProxyWatch",
        "events": ["alert.fired", "alert.resolved"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["registered"] is True
    assert data["type"] == "slack"
    assert data["username"] == "ProxyWatch"


@pytest.mark.asyncio
async def test_register_discord_integration(client):
    response = await client.post("/integrations", json={
        "type": "discord",
        "webhook_url": "https://discord.com/api/webhooks/TEST",
        "username": "ProxyWatch",
        "events": ["alert.fired", "alert.resolved"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["registered"] is True
    assert data["type"] == "discord"
    assert data["username"] == "ProxyWatch"
