import asyncio
from app.state import AppState
from app.prober import run_probe_round
from app.analyzer import calculate_failure_rate
from app.alert_manager import evaluate_alerts


async def scheduler_loop(state: AppState) -> None:
    while True:
        try:
            await run_probe_round(state)
            failure_rate = calculate_failure_rate(state)
            await evaluate_alerts(state, failure_rate)
        except Exception:
            pass

        await asyncio.sleep(state.config.check_interval_seconds)
