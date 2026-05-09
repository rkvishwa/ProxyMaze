from app.models import CheckStatus
from app.state import AppState


def calculate_failure_rate(state: AppState) -> float:
    probed = [p for p in state.proxies.values() if p.status != CheckStatus.PENDING]
    if not probed:
        return 0.0

    total = len(probed)
    down = sum(1 for p in probed if p.status == CheckStatus.DOWN)
    return down / total
