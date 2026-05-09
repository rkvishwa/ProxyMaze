from app.models import Integration, IntegrationType
from app.state import AppState


def add_integration(state: AppState, integration: Integration) -> None:
    state.integrations.append(integration)


def _parse_timestamp(payload: dict) -> float:
    ts_str = payload.get("fired_at") or payload.get("resolved_at", "")
    if not ts_str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()
    try:
        from datetime import datetime, timezone
        dt = datetime.strptime(ts_str.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
        return dt.timestamp()
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).timestamp()


def format_slack_message(payload: dict, username: str) -> dict:
    event = payload.get("event", "")
    alert_id = payload.get("alert_id", "")
    failure_rate = payload.get("failure_rate", 0.0)
    total_proxies = payload.get("total_proxies", 0)
    failed_proxies = payload.get("failed_proxies", 0)
    failed_proxy_ids = payload.get("failed_proxy_ids", [])
    threshold = payload.get("threshold", 0.2)
    message = payload.get("message", "")

    if event == "alert.fired":
        fired_at = payload.get("fired_at", "")
        summary = message or "Proxy pool failure rate exceeded threshold"
        color = "#FF0000"
        footer_ts = _parse_timestamp(payload)
        fields = [
            {"title": "Alert ID", "value": alert_id},
            {"title": "Failure Rate", "value": f"{failure_rate:.2f}"},
            {"title": "Failed Proxies", "value": str(failed_proxies)},
            {"title": "Threshold", "value": str(threshold)},
            {"title": "Failed IDs", "value": ", ".join(failed_proxy_ids) if failed_proxy_ids else "None"},
            {"title": "Fired At", "value": fired_at},
        ]
    else:
        resolved_at = payload.get("resolved_at", "")
        fired_at = payload.get("fired_at", "")
        summary = f"Alert {alert_id} resolved at {resolved_at}"
        color = "#00FF00"
        footer_ts = _parse_timestamp(payload)
        fields = [
            {"title": "Alert ID", "value": alert_id},
            {"title": "Failure Rate", "value": f"{failure_rate:.2f}"},
            {"title": "Failed Proxies", "value": str(failed_proxies)},
            {"title": "Threshold", "value": str(threshold)},
            {"title": "Failed IDs", "value": ", ".join(failed_proxy_ids) if failed_proxy_ids else "None"},
            {"title": "Fired At", "value": fired_at},
            {"title": "Resolved At", "value": resolved_at},
        ]

    return {
        "username": username,
        "text": summary,
        "attachments": [
            {
                "color": color,
                "fields": fields,
                "footer": "ProxyMaze",
                "ts": int(footer_ts),
            }
        ],
    }


def format_discord_message(payload: dict) -> dict:
    event = payload.get("event", "")
    alert_id = payload.get("alert_id", "")
    failure_rate = payload.get("failure_rate", 0.0)
    total_proxies = payload.get("total_proxies", 0)
    failed_proxies = payload.get("failed_proxies", 0)
    failed_proxy_ids = payload.get("failed_proxy_ids", [])
    threshold = payload.get("threshold", 0.2)
    message = payload.get("message", "")

    if event == "alert.fired":
        color = 16711680
        summary = message or "Proxy pool failure rate exceeded threshold"
        title = "Alert Fired"
    else:
        color = 65280
        summary = f"Alert {alert_id} has been resolved"
        title = "Alert Resolved"

    embed = {
        "title": title,
        "description": summary,
        "color": color,
        "fields": [
            {"name": "Alert ID", "value": alert_id},
            {"name": "Failure Rate", "value": f"{failure_rate:.2f}"},
            {"name": "Failed Proxies", "value": str(failed_proxies)},
            {"name": "Threshold", "value": str(threshold)},
            {"name": "Failed IDs", "value": ", ".join(failed_proxy_ids) if failed_proxy_ids else "None"},
        ],
        "footer": {"text": "ProxyMaze"},
    }

    return {"embeds": [embed]}
