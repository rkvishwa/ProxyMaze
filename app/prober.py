import asyncio
from datetime import datetime, timezone
import httpx
from app.models import CheckStatus, ProxyCheck
from app.state import AppState


async def probe_proxy_url(url: str, timeout_ms: int) -> ProxyCheck:
    timeout_seconds = timeout_ms / 1000.0
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout_seconds)
        if 200 <= response.status_code < 300:
            return ProxyCheck(timestamp=timestamp, status=CheckStatus.UP)
        else:
            return ProxyCheck(timestamp=timestamp, status=CheckStatus.DOWN)
    except (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.NetworkError,
        httpx.ReadError,
        httpx.WriteError,
    ):
        return ProxyCheck(timestamp=timestamp, status=CheckStatus.DOWN)


async def run_probe_round(state: AppState) -> None:
    if not state.proxies:
        return

    config = state.config
    proxy_list = list(state.proxies.values())

    tasks = [probe_proxy_url(p.url, config.request_timeout_ms) for p in proxy_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    async with state.lock:
        for proxy, result in zip(proxy_list, results):
            if isinstance(result, Exception):
                check = ProxyCheck(
                    timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    status=CheckStatus.DOWN,
                )
            else:
                check = result

            proxy.history.append(check)
            proxy.status = check.status
            state.total_checks += 1
