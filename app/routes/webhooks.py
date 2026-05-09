from fastapi import APIRouter, Request
from app.models import Webhook
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/webhooks")
async def register_webhook(body: Webhook, request: Request) -> dict:
    state: AppState = get_state(request)
    async with state.lock:
        state.webhooks.append(body)
    return {"registered": True, "url": body.url}
