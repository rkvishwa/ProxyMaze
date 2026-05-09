import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.state import AppState


@pytest.fixture
async def client():
    app.state.app_state = AppState()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.state.app_state = None


@pytest.fixture
async def client_with_proxies(client):
    await client.post("/proxies", json={
        "proxies": [
            "http://example.com/px-101",
            "http://example.com/px-102",
            "http://example.com/px-103",
            "http://example.com/px-104",
            "http://example.com/px-105",
        ],
        "replace": True
    })
    yield client
