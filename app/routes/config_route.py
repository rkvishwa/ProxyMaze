from fastapi import APIRouter, Request
from app.models import ConfigUpdate
from app.config import AppConfig
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/config")
async def update_config(body: ConfigUpdate, request: Request) -> AppConfig:
    state: AppState = get_state(request)
    async with state.lock:
        if body.check_interval_seconds is not None:
            state.config.check_interval_seconds = body.check_interval_seconds
        if body.request_timeout_ms is not None:
            state.config.request_timeout_ms = body.request_timeout_ms
    return state.config
