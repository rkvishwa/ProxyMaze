import pytest


@pytest.mark.asyncio
async def test_metrics_initial(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 0
    assert data["current_pool_size"] == 0
    assert data["active_alerts"] == 0
    assert data["total_alerts"] == 0
    assert data["webhook_deliveries"] == 0
