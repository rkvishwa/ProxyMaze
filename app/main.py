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

app.include_router(health.router)
app.include_router(config_route.router)
app.include_router(proxies.router)
app.include_router(alerts.router)
app.include_router(webhooks.router)
app.include_router(integrations_route.router)
app.include_router(metrics.router)
