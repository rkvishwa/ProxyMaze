import asyncio
from datetime import datetime, timezone
import httpx
from app.state import AppState
from app.models import Alert, WebhookPayload, IntegrationType
from app.integrations import format_slack_message, format_discord_message


RETRY_STATUS_CODES = {500, 502, 503, 504}
MAX_DELIVERY_SECONDS = 60


async def _post_with_retry(url: str, json_payload: dict) -> bool:
    start = asyncio.get_event_loop().time()
    delay = 1.0

    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=json_payload, timeout=10.0)
            if response.status_code < 500:
                return True
            if response.status_code not in RETRY_STATUS_CODES:
                return False
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
        ):
            pass

        elapsed = asyncio.get_event_loop().time() - start
        if elapsed + delay > MAX_DELIVERY_SECONDS:
            return False

        await asyncio.sleep(delay)
        delay = min(delay * 2, 10.0)


async def dispatch_alert_event(state: AppState, alert: Alert, event: str) -> None:
    base_payload = WebhookPayload(
        event=event,
        alert_id=alert.alert_id,
        failure_rate=alert.failure_rate,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    tasks: list[asyncio.Task[bool]] = []

    for webhook in state.webhooks:
        tasks.append(asyncio.create_task(_post_with_retry(webhook.url, base_payload.model_dump())))

    for integration in state.integrations:
        raw = base_payload.model_dump()
        if integration.type == IntegrationType.SLACK:
            payload = format_slack_message(raw)
        else:
            payload = format_discord_message(raw)
        tasks.append(asyncio.create_task(_post_with_retry(integration.webhook_url, payload)))

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, bool) and result:
            state.webhook_deliveries += 1
