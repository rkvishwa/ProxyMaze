from datetime import datetime, timezone
import uuid
from app.analyzer import get_failure_snapshot
from app.models import Alert, AlertStatus
from app.state import AppState
from app.webhook_delivery import dispatch_alert_event


BREACH_THRESHOLD = 0.20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_active_alert_locked(state: AppState) -> Alert | None:
    if state.active_alert is None:
        return None

    state.active_alert.status = AlertStatus.RESOLVED
    state.active_alert.resolved_at = _utc_now()
    alert_snapshot = state.active_alert.model_copy(deep=True)
    state.active_alert = None
    return alert_snapshot


def evaluate_alerts_locked(
    state: AppState, failure_rate: float | None = None
) -> tuple[str, Alert] | None:
    summary = get_failure_snapshot(state)
    active_failure_rate = summary.failure_rate if failure_rate is None else failure_rate

    if active_failure_rate >= BREACH_THRESHOLD:
        if state.active_alert is None:
            alert = Alert(
                alert_id=f"alert-{uuid.uuid4().hex[:8]}",
                status=AlertStatus.ACTIVE,
                failure_rate=round(active_failure_rate, 4),
                total_proxies=summary.total_proxies,
                failed_proxies=summary.failed_proxies,
                failed_proxy_ids=summary.failed_proxy_ids.copy(),
                threshold=BREACH_THRESHOLD,
                fired_at=_utc_now(),
                message="Proxy pool failure rate exceeded threshold",
            )
            state.active_alert = alert
            state.alerts.append(alert)
            return ("alert.fired", alert.model_copy(deep=True))

        state.active_alert.failure_rate = round(active_failure_rate, 4)
        state.active_alert.total_proxies = summary.total_proxies
        state.active_alert.failed_proxies = summary.failed_proxies
        state.active_alert.failed_proxy_ids = summary.failed_proxy_ids.copy()
        return None

    resolved_alert = resolve_active_alert_locked(state)
    if resolved_alert is None:
        return None
    return ("alert.resolved", resolved_alert)


async def evaluate_alerts(state: AppState, failure_rate: float | None = None) -> None:
    async with state.lock:
        event = evaluate_alerts_locked(state, failure_rate)

    if event:
        await dispatch_alert_event(state, event[1], event[0])
