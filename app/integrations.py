from app.models import Integration, IntegrationType
from app.state import AppState


def add_integration(state: AppState, integration: Integration) -> None:
    state.integrations.append(integration)


def format_slack_message(payload: dict) -> dict:
    event = payload.get("event", "")
    alert_id = payload.get("alert_id", "")
    failure_rate = payload.get("failure_rate", 0.0)
    timestamp = payload.get("timestamp", "")

    if event == "alert.fired":
        text = (
            f":warning: *Alert Fired*\n"
            f"*Alert ID:* {alert_id}\n"
            f"*Failure Rate:* {failure_rate:.2%}\n"
            f"*Triggered At:* {timestamp}"
        )
    else:
        text = (
            f":white_check_mark: *Alert Resolved*\n"
            f"*Alert ID:* {alert_id}\n"
            f"*Failure Rate:* {failure_rate:.2%}\n"
            f"*Resolved At:* {timestamp}"
        )

    return {"text": text}


def format_discord_message(payload: dict) -> dict:
    event = payload.get("event", "")
    alert_id = payload.get("alert_id", "")
    failure_rate = payload.get("failure_rate", 0.0)
    timestamp = payload.get("timestamp", "")

    if event == "alert.fired":
        content = (
            f"\u26a0\ufe0f **Alert Fired**\n"
            f"**Alert ID:** {alert_id}\n"
            f"**Failure Rate:** {failure_rate:.2%}\n"
            f"**Triggered At:** {timestamp}"
        )
    else:
        content = (
            f"\u2705 **Alert Resolved**\n"
            f"**Alert ID:** {alert_id}\n"
            f"**Failure Rate:** {failure_rate:.2%}\n"
            f"**Resolved At:** {timestamp}"
        )

    return {"content": content}
