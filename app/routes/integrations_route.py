from fastapi import APIRouter, Request
from app.models import Integration
from app.state import AppState
from app.integrations import add_integration

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/integrations", status_code=201)
async def register_integration(body: Integration, request: Request) -> dict:
    state: AppState = get_state(request)
    async with state.lock:
        add_integration(state, body)
    return {
        "registered": True,
        "type": body.type,
        "webhook_url": body.webhook_url,
        "username": body.username,
        "events": body.events,
    }
