from fastapi import APIRouter, Request
from app.models import Alert
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get("/alerts", response_model=list[Alert])
async def list_alerts(request: Request) -> list[Alert]:
    state: AppState = get_state(request)
    return state.alerts
