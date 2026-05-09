from fastapi import APIRouter, Request
from app.models import Metrics
from app.state import AppState

router = APIRouter()


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


@router.get("/metrics", response_model=Metrics)
async def get_metrics(request: Request) -> Metrics:
    state: AppState = get_state(request)
    return state.get_metrics()
