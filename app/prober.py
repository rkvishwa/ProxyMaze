import asyncio
from datetime import datetime, timezone
import httpx
from app.alert_manager import evaluate_alerts_locked
from app.models import CheckStatus, ProxyCheck
from app.state import AppState
from app.webhook_delivery import dispatch_alert_event


async def probe_proxy_url(url: str, timeout_ms: int) -> ProxyCheck:
    timeout_seconds = timeout_ms / 1000.0
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=timeout_seconds,
                follow_redirects=True,
            )
        if 200 <= response.status_code < 300:
            return ProxyCheck(checked_at=checked_at, status=CheckStatus.UP)
        else:
            return ProxyCheck(checked_at=checked_at, status=CheckStatus.DOWN)
    except (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.NetworkError,
        httpx.ReadError,
        httpx.WriteError,
    ):
        return ProxyCheck(checked_at=checked_at, status=CheckStatus.DOWN)


async def run_probe_round(state: AppState) -> None:
    async with state.lock:
        proxy_list = list(state.proxies.values())
        timeout_ms = state.config.request_timeout_ms

    if not proxy_list:
        return

    tasks = [probe_proxy_url(proxy.url, timeout_ms) for proxy in proxy_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    event: tuple[str, object] | None = None
    async with state.lock:
        for proxy, result in zip(proxy_list, results):
            if isinstance(result, Exception):
                check = ProxyCheck(
                    checked_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    status=CheckStatus.DOWN,
                )
            else:
                check = result

            proxy.history.append(check)
            proxy.status = check.status
            proxy.last_checked_at = check.checked_at
            if check.status == CheckStatus.DOWN:
                proxy.consecutive_failures += 1
            else:
                proxy.consecutive_failures = 0
            state.total_checks += 1

        event = evaluate_alerts_locked(state)

    if event:
        await dispatch_alert_event(state, event[1], event[0])
