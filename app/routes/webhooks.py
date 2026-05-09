from fastapi import APIRouter, Request
import uuid
from app.models import Webhook
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/webhooks", status_code=201)
async def register_webhook(request: Request) -> dict:
    state: AppState = get_state(request)
    try:
        data = await request.json()
    except Exception:
        return {"error": "Invalid JSON body"}
    url = data.get("url")
    if not url:
        return {"error": "url is required"}

    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"
    webhook = Webhook(webhook_id=webhook_id, url=url)
    async with state.lock:
        state.webhooks.append(webhook)
    return {"webhook_id": webhook.webhook_id, "url": webhook.url}
