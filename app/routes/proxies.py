import re
from fastapi import APIRouter, Request, HTTPException, Response
from app.alert_manager import resolve_active_alert_locked
from app.analyzer import calculate_failure_rate
from app.models import Proxy, ProxyIn, ProxyView, ProxyDetailView, CheckStatus
from app.state import AppState
from app.webhook_delivery import dispatch_alert_event

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def extract_proxy_id(url: str) -> str:
    match = re.search(r"/([^/]+)/?$", url)
    if not match:
        raise HTTPException(status_code=400, detail=f"Cannot extract ID from URL: {url}")
    return match.group(1)


@router.post("/proxies", status_code=201)
async def add_proxies(body: ProxyIn, request: Request) -> dict:
    state: AppState = get_state(request)
    resolved_alert = None
    async with state.lock:
        if body.replace:
            resolved_alert = resolve_active_alert_locked(state)
            state.proxies.clear()
        accepted_proxies = []
        for url in body.proxies:
            proxy_id = extract_proxy_id(url)
            proxy = Proxy(id=proxy_id, url=url)
            state.proxies[proxy_id] = proxy
            accepted_proxies.append(proxy)
    state.wake_scheduler()
    if resolved_alert is not None:
        await dispatch_alert_event(state, resolved_alert, "alert.resolved")
    return {
        "accepted": len(accepted_proxies),
        "proxies": [
            {"id": p.id, "url": p.url, "status": p.status} for p in accepted_proxies
        ],
    }


@router.get("/proxies")
async def list_proxies(request: Request) -> dict:
    state: AppState = get_state(request)
    async with state.lock:
        proxy_list = [proxy.model_copy(deep=True) for proxy in state.proxies.values()]
        total = len(proxy_list)
        up = sum(1 for proxy in proxy_list if proxy.status == CheckStatus.UP)
        down = sum(1 for proxy in proxy_list if proxy.status == CheckStatus.DOWN)
        failure_rate = calculate_failure_rate(state)

        proxies = [
            ProxyView(
                id=proxy.id,
                url=proxy.url,
                status=proxy.status,
                last_checked_at=proxy.last_checked_at,
                consecutive_failures=proxy.consecutive_failures,
            )
            for proxy in proxy_list
        ]

    return {
        "total": total,
        "up": up,
        "down": down,
        "failure_rate": failure_rate,
        "proxies": [proxy.model_dump() for proxy in proxies],
    }


@router.get("/proxies/{proxy_id}", response_model=ProxyDetailView)
async def get_proxy(proxy_id: str, request: Request) -> ProxyDetailView:
    state: AppState = get_state(request)
    async with state.lock:
        proxy = state.proxies.get(proxy_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        proxy = proxy.model_copy(deep=True)
    return ProxyDetailView(
        id=proxy.id,
        url=proxy.url,
        status=proxy.status,
        last_checked_at=proxy.last_checked_at,
        consecutive_failures=proxy.consecutive_failures,
        total_checks=proxy.total_checks,
        uptime_percentage=proxy.uptime_percentage,
        history=proxy.history,
    )


@router.get("/proxies/{proxy_id}/history")
async def get_proxy_history(proxy_id: str, request: Request) -> list[dict]:
    state: AppState = get_state(request)
    async with state.lock:
        proxy = state.proxies.get(proxy_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        history = [check.model_copy(deep=True) for check in proxy.history]
    return [{"checked_at": check.checked_at, "status": check.status} for check in history]


@router.delete("/proxies", status_code=204)
async def delete_proxies(request: Request) -> Response:
    state: AppState = get_state(request)
    resolved_alert = None
    async with state.lock:
        resolved_alert = resolve_active_alert_locked(state)
        state.proxies.clear()
    state.wake_scheduler()
    if resolved_alert is not None:
        await dispatch_alert_event(state, resolved_alert, "alert.resolved")
    return Response(status_code=204)
