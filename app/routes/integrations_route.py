from fastapi import APIRouter, Request
from app.models import Integration
from app.state import AppState
from app.integrations import add_integration

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/integrations")
async def register_integration(body: Integration, request: Request) -> dict:
    state: AppState = get_state(request)
    add_integration(state, body)
    return {"registered": True, "type": body.type, "webhook_url": body.webhook_url}
