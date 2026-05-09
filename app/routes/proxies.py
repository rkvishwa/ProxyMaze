import re
from fastapi import APIRouter, Request, HTTPException
from app.models import Proxy, ProxyIn, ProxyView, ProxyDetailView
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def extract_proxy_id(url: str) -> str:
    match = re.search(r"/([^/]+)/?$", url)
    if not match:
        raise HTTPException(status_code=400, detail=f"Cannot extract ID from URL: {url}")
    return match.group(1)


@router.post("/proxies")
async def add_proxies(body: ProxyIn, request: Request) -> dict:
    state: AppState = get_state(request)
    async with state.lock:
        if body.replace:
            state.proxies.clear()
        for url in body.urls:
            proxy_id = extract_proxy_id(url)
            state.proxies[proxy_id] = Proxy(id=proxy_id, url=url)
    return {"added": len(body.urls), "replaced": body.replace}


@router.get("/proxies", response_model=list[ProxyView])
async def list_proxies(request: Request) -> list[ProxyView]:
    state: AppState = get_state(request)
    return [
        ProxyView(id=p.id, url=p.url, status=p.status)
        for p in state.proxies.values()
    ]


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
        uptime_percentage=proxy.uptime_percentage,
        history=proxy.history,
    )


@router.delete("/proxies")
async def delete_proxies(request: Request) -> dict:
    state: AppState = get_state(request)
    async with state.lock:
        state.proxies.clear()
    return {"deleted": True}
