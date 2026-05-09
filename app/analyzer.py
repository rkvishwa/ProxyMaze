from app.models import CheckStatus
from app.state import AppState


def calculate_failure_rate(state: AppState) -> float:
    if not state.proxies:
        return 0.0

    total = len(state.proxies)
    down = sum(1 for p in state.proxies.values() if p.status == CheckStatus.DOWN)
    return down / total
