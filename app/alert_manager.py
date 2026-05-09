from datetime import datetime, timezone
import uuid
from app.models import Alert, AlertStatus, CheckStatus
from app.state import AppState
from app.webhook_delivery import dispatch_alert_event


BREACH_THRESHOLD = 0.20


async def evaluate_alerts(state: AppState, failure_rate: float) -> None:
    async with state.lock:
        if failure_rate >= BREACH_THRESHOLD:
            if state.active_alert is None:
                probed_proxies = [
                    p for p in state.proxies.values() if p.status != CheckStatus.PENDING
                ]
                down_proxy_ids = [
                    p.id for p in probed_proxies if p.status == CheckStatus.DOWN
                ]
                total_proxies = len(probed_proxies)
                failed_proxies = len(down_proxy_ids)
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    status=AlertStatus.ACTIVE,
                    failure_rate=round(failure_rate, 4),
                    total_proxies=total_proxies,
                    failed_proxies=failed_proxies,
                    failed_proxy_ids=down_proxy_ids,
                    threshold=0.2,
                    fired_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    message="Proxy pool failure rate exceeded threshold",
                )
                state.active_alert = alert
                state.alerts.append(alert)
                event = ("alert.fired", alert)
            else:
                # Ongoing breach -- update alert to reflect current pool state.
                down_proxy_ids_now = [
                    p.id for p in state.proxies.values() if p.status == CheckStatus.DOWN
                ]
                state.active_alert.failure_rate = round(failure_rate, 4)
                state.active_alert.total_proxies = len(state.proxies)
                state.active_alert.failed_proxies = len(down_proxy_ids_now)
                state.active_alert.failed_proxy_ids = down_proxy_ids_now
                event = None
        else:
            if state.active_alert is not None:
                alert = state.active_alert
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                state.active_alert = None
                event = ("alert.resolved", alert)
            else:
                event = None

    if event:
        await dispatch_alert_event(state, event[1], event[0])
