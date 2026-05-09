import pytest
from app.models import CheckStatus


@pytest.mark.asyncio
async def test_alert_excludes_pending_proxies(client):
    state = client._transport.app.state.app_state

    async with state.lock:
        state.proxies.clear()
        for i in range(4):
            from app.models import Proxy
            p = Proxy(id=f"px-{i}", url=f"http://example.com/px-{i}")
            if i < 2:
                p.status = CheckStatus.DOWN
            else:
                p.status = CheckStatus.PENDING
            state.proxies[p.id] = p

    from app.analyzer import calculate_failure_rate
    from app.alert_manager import evaluate_alerts

    failure_rate = calculate_failure_rate(state)
    assert failure_rate == 1.0

    await evaluate_alerts(state, failure_rate)
    assert state.active_alert is not None
    assert state.active_alert.total_proxies == 2
    assert state.active_alert.failed_proxies == 2
    response = await client.get("/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["total_proxies"] == 2
    assert alerts[0]["failed_proxies"] == 2
    assert alerts[0]["failed_proxy_ids"] == ["px-0", "px-1"]


@pytest.mark.asyncio
async def test_alert_lifecycle_single_active(client):
    state = client._transport.app.state.app_state

    async with state.lock:
        state.proxies.clear()
        for i in range(5):
            from app.models import Proxy
            p = Proxy(id=f"px-{i}", url=f"http://example.com/px-{i}")
            p.status = CheckStatus.DOWN
            state.proxies[p.id] = p

    from app.analyzer import calculate_failure_rate
    from app.alert_manager import evaluate_alerts

    failure_rate = calculate_failure_rate(state)
    assert failure_rate == 1.0

    await evaluate_alerts(state, failure_rate)

    assert state.active_alert is not None
    first_alert_id = state.active_alert.alert_id

    await evaluate_alerts(state, failure_rate)
    assert state.active_alert.alert_id == first_alert_id

    async with state.lock:
        for p in state.proxies.values():
            p.status = CheckStatus.UP

    failure_rate = calculate_failure_rate(state)
    assert failure_rate == 0.0

    await evaluate_alerts(state, failure_rate)
    assert state.active_alert is None
    assert len(state.alerts) == 1
    assert state.alerts[0].status.value == "resolved"

    async with state.lock:
        for p in state.proxies.values():
            p.status = CheckStatus.DOWN

    failure_rate = calculate_failure_rate(state)
    await evaluate_alerts(state, failure_rate)
    assert state.active_alert is not None
    assert state.active_alert.alert_id != first_alert_id
    assert len(state.alerts) == 2


@pytest.mark.asyncio
async def test_alert_fields_update_during_ongoing_breach(client):
    state = client._transport.app.state.app_state

    async with state.lock:
        state.proxies.clear()
        for i in range(5):
            from app.models import Proxy
            p = Proxy(id=f"px-{i}", url=f"http://example.com/px-{i}")
            p.status = CheckStatus.DOWN
            state.proxies[p.id] = p

    from app.analyzer import calculate_failure_rate
    from app.alert_manager import evaluate_alerts

    failure_rate = calculate_failure_rate(state)
    await evaluate_alerts(state, failure_rate)

    alert = state.active_alert
    assert alert is not None
    assert alert.failed_proxy_ids == ["px-0", "px-1", "px-2", "px-3", "px-4"]

    # Simulate one proxy recovering while breach continues
    async with state.lock:
        state.proxies["px-4"].status = CheckStatus.UP

    failure_rate = calculate_failure_rate(state)
    await evaluate_alerts(state, failure_rate)

    assert state.active_alert.alert_id == alert.alert_id
    assert state.active_alert.failed_proxy_ids == ["px-0", "px-1", "px-2", "px-3"]
    assert state.active_alert.failed_proxies == 4
    assert state.active_alert.total_proxies == 5
    assert state.active_alert.failure_rate == round(failure_rate, 4)

    response = await client.get("/alerts")
    alerts = response.json()
    assert alerts[0]["failed_proxy_ids"] == ["px-0", "px-1", "px-2", "px-3"]

