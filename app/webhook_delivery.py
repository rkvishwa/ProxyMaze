import asyncio
from datetime import datetime, timezone
import httpx
from app.state import AppState
from app.models import Alert, IntegrationType
from app.integrations import format_slack_message, format_discord_message


RETRY_STATUS_CODES = {500, 502, 503, 504}
MAX_DELIVERY_SECONDS = 60
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


async def _post_with_retry(url: str, json_payload: dict) -> bool:
    start = asyncio.get_running_loop().time()
    delay = 1.0

    while True:
        try:
            async with httpx.AsyncClient() as client:
                current_url = url
                redirects_followed = 0

                while True:
                    response = await client.post(
                        current_url,
                        json=json_payload,
                        timeout=10.0,
                        follow_redirects=False,
                    )
                    if response.status_code not in REDIRECT_STATUS_CODES:
                        break

                    location = response.headers.get("Location")
                    if not location or redirects_followed >= MAX_REDIRECTS:
                        return False

                    current_url = str(httpx.URL(current_url).join(location))
                    redirects_followed += 1
            if 200 <= response.status_code < 300:
                return True
            if response.status_code not in RETRY_STATUS_CODES:
                return False
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
        ):
            pass

        elapsed = asyncio.get_running_loop().time() - start
        if elapsed + delay > MAX_DELIVERY_SECONDS:
            return False

        await asyncio.sleep(delay)
        delay = min(delay * 2, 10.0)


def _build_fired_payload(alert: Alert) -> dict:
    return {
        "event": "alert.fired",
        "alert_id": alert.alert_id,
        "fired_at": alert.fired_at,
        "failure_rate": alert.failure_rate,
        "total_proxies": alert.total_proxies,
        "failed_proxies": alert.failed_proxies,
        "failed_proxy_ids": alert.failed_proxy_ids,
        "threshold": alert.threshold,
        "message": alert.message,
    }


def _build_resolved_payload(alert: Alert) -> dict:
    return {
        "event": "alert.resolved",
        "alert_id": alert.alert_id,
        "resolved_at": alert.resolved_at,
    }


async def dispatch_alert_event(state: AppState, alert: Alert, event: str) -> None:
    if event == "alert.fired":
        base_payload = _build_fired_payload(alert)
    else:
        base_payload = _build_resolved_payload(alert)

    async with state.lock:
        webhooks = [webhook.model_copy(deep=True) for webhook in state.webhooks]
        integrations = [integration.model_copy(deep=True) for integration in state.integrations]

    tasks: list[asyncio.Task[bool]] = []

    for webhook in webhooks:
        tasks.append(asyncio.create_task(_post_with_retry(webhook.url, base_payload)))

    for integration in integrations:
        if event not in integration.events:
            continue

        integration_payload = {
            **base_payload,
            "fired_at": alert.fired_at,
            "failure_rate": alert.failure_rate,
            "total_proxies": alert.total_proxies,
            "failed_proxies": alert.failed_proxies,
            "failed_proxy_ids": alert.failed_proxy_ids,
            "threshold": alert.threshold,
            "message": alert.message,
        }
        if integration.type == IntegrationType.SLACK:
            payload = format_slack_message(integration_payload, integration.username)
        else:
            payload = format_discord_message(integration_payload)
        tasks.append(asyncio.create_task(_post_with_retry(integration.webhook_url, payload)))

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_deliveries = sum(1 for result in results if isinstance(result, bool) and result)
    if successful_deliveries:
        async with state.lock:
            state.webhook_deliveries += successful_deliveries
