import re
from fastapi import APIRouter, Request, HTTPException, Response
from app.models import Proxy, ProxyIn, ProxyView, ProxyDetailView, CheckStatus
from app.state import AppState

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
    async with state.lock:
        if body.replace:
            if state.active_alert is not None:
                from datetime import datetime, timezone
                from app.models import AlertStatus
                state.active_alert.status = AlertStatus.RESOLVED
                state.active_alert.resolved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                state.active_alert = None
            state.proxies.clear()
        accepted_proxies = []
        for url in body.proxies:
            proxy_id = extract_proxy_id(url)
            proxy = Proxy(id=proxy_id, url=url)
            state.proxies[proxy_id] = proxy
            accepted_proxies.append(proxy)
    return {
        "accepted": len(accepted_proxies),
        "proxies": [
            {"id": p.id, "url": p.url, "status": p.status} for p in accepted_proxies
        ],
    }


@router.get("/proxies")
async def list_proxies(request: Request) -> dict:
    state: AppState = get_state(request)
    proxy_list = list(state.proxies.values())
    total = len(proxy_list)
    up = sum(1 for p in proxy_list if p.status == CheckStatus.UP)
    down = sum(1 for p in proxy_list if p.status == CheckStatus.DOWN)
    failure_rate = down / total if total > 0 else 0.0

    proxies = [
        ProxyView(
            id=p.id,
            url=p.url,
            status=p.status,
            last_checked_at=p.last_checked_at,
            consecutive_failures=p.consecutive_failures,
        )
        for p in proxy_list
    ]

    return {
        "total": total,
        "up": up,
        "down": down,
        "failure_rate": failure_rate,
        "proxies": [p.model_dump() for p in proxies],
    }


@router.get("/proxies/{proxy_id}", response_model=ProxyDetailView)
async def get_proxy(proxy_id: str, request: Request) -> ProxyDetailView:
    state: AppState = get_state(request)
    proxy = state.proxies.get(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
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
    proxy = state.proxies.get(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return [{"checked_at": c.checked_at, "status": c.status} for c in proxy.history]


@router.delete("/proxies", status_code=204)
async def delete_proxies(request: Request) -> Response:
    state: AppState = get_state(request)
    async with state.lock:
        state.proxies.clear()
    return Response(status_code=204)
