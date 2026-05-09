from fastapi import APIRouter, Request
import uuid
from app.models import Webhook, WebhookIn
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/webhooks", status_code=201)
async def register_webhook(body: WebhookIn, request: Request) -> dict:
    state: AppState = get_state(request)
    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"
    webhook = Webhook(webhook_id=webhook_id, url=body.url)
    async with state.lock:
        state.webhooks.append(webhook)
    return {"webhook_id": webhook.webhook_id, "url": webhook.url}
