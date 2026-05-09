import asyncio
from typing import Dict, List
from app.models import Alert, Proxy, Webhook, Integration, Metrics
from app.config import AppConfig


class AppState:
    def __init__(self) -> None:
        self.config: AppConfig = AppConfig()
        self.proxies: Dict[str, Proxy] = {}
        self.alerts: List[Alert] = []
        self.active_alert: Alert | None = None
        self.webhooks: List[Webhook] = []
        self.integrations: List[Integration] = []
        self.scheduler_task: asyncio.Task | None = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.scheduler_wakeup: asyncio.Event = asyncio.Event()

        # Metrics counters
        self.total_checks: int = 0
        self.webhook_deliveries: int = 0

    def wake_scheduler(self) -> None:
        self.scheduler_wakeup.set()

    def get_proxy_count(self) -> int:
        return len(self.proxies)

    def get_metrics(self) -> Metrics:
        return Metrics(
            total_checks=self.total_checks,
            current_pool_size=len(self.proxies),
            active_alerts=1 if self.active_alert else 0,
            total_alerts=len(self.alerts),
            webhook_deliveries=self.webhook_deliveries,
        )
