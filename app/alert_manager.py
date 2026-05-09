from datetime import datetime, timezone
import uuid
from app.models import Alert, AlertStatus
from app.state import AppState
from app.webhook_delivery import dispatch_alert_event


BREACH_THRESHOLD = 0.20


async def evaluate_alerts(state: AppState, failure_rate: float) -> None:
    async with state.lock:
        if failure_rate >= BREACH_THRESHOLD:
            if state.active_alert is None:
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    status=AlertStatus.ACTIVE,
                    failure_rate=round(failure_rate, 4),
                    triggered_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
                state.active_alert = alert
                state.alerts.append(alert)
                await dispatch_alert_event(state, alert, "alert.fired")
        else:
            if state.active_alert is not None:
                alert = state.active_alert
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                state.active_alert = None
                await dispatch_alert_event(state, alert, "alert.resolved")
