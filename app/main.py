from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.state import AppState
from app.scheduler import scheduler_loop
from app.routes import (
    health,
    config_route,
    proxies,
    alerts,
    webhooks,
    integrations_route,
    metrics,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state = AppState()
    app.state.app_state = app_state
    app_state.scheduler_task = __import__("asyncio").create_task(scheduler_loop(app_state))
    yield
    if app_state.scheduler_task:
        app_state.scheduler_task.cancel()
        try:
            await app_state.scheduler_task
        except Exception:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root() -> dict:
    return {
        "service": "ProxyMaze Watchtower",
        "endpoints": {
            "GET /": "This index. Lists all available endpoints.",
            "GET /health": "Service health check. Returns {\"status\": \"ok\"}.",
            "POST /config": "Update check_interval_seconds and/or request_timeout_ms. Applied immediately.",
            "POST /proxies": "Add proxy URLs to the pool. Extracts IDs from URL paths. Use {\"replace\": true} to clear existing pool first.",
            "GET /proxies": "List all proxies with their current status from the last background check.",
            "GET /proxies/{id}": "Get proxy detail including uptime_percentage and full check history.",
            "DELETE /proxies": "Clear the proxy pool. Alert history is preserved.",
            "GET /alerts": "List all alerts (active and resolved).",
            "POST /webhooks": "Register a webhook URL to receive alert.fired and alert.resolved JSON payloads.",
            "POST /integrations": "Register a Slack or Discord integration for formatted alert notifications.",
            "GET /metrics": "Summary counters: total_checks, active_alerts, webhook_deliveries.",
        },
    }


app.include_router(health.router)
app.include_router(config_route.router)
app.include_router(proxies.router)
app.include_router(alerts.router)
app.include_router(webhooks.router)
app.include_router(integrations_route.router)
app.include_router(metrics.router)
