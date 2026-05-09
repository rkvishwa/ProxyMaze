import asyncio
from app.state import AppState
from app.prober import run_probe_round


async def scheduler_loop(state: AppState) -> None:
    while True:
        try:
            await run_probe_round(state)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

        try:
            await asyncio.wait_for(
                state.scheduler_wakeup.wait(),
                timeout=state.config.check_interval_seconds,
            )
            state.scheduler_wakeup.clear()
        except asyncio.TimeoutError:
            pass
