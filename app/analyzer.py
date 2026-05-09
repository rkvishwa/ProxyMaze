from dataclasses import dataclass

from app.models import CheckStatus
from app.state import AppState


@dataclass(frozen=True)
class FailureSnapshot:
    total_proxies: int
    failed_proxies: int
    failed_proxy_ids: list[str]
    failure_rate: float


def get_failure_snapshot(state: AppState) -> FailureSnapshot:
    probed = [p for p in state.proxies.values() if p.status != CheckStatus.PENDING]
    failed_proxy_ids = [p.id for p in probed if p.status == CheckStatus.DOWN]
    total_proxies = len(probed)
    failed_proxies = len(failed_proxy_ids)
    failure_rate = failed_proxies / total_proxies if total_proxies else 0.0

    return FailureSnapshot(
        total_proxies=total_proxies,
        failed_proxies=failed_proxies,
        failed_proxy_ids=failed_proxy_ids,
        failure_rate=failure_rate,
    )


def calculate_failure_rate(state: AppState) -> float:
    return get_failure_snapshot(state).failure_rate
