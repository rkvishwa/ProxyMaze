import asyncio
from typing import Dict, List, Optional
from app.models import Alert, Proxy, Webhook, Integration, Metrics
from app.config import AppConfig


class AppState:
    def __init__(self) -> None:
        self.config: AppConfig = AppConfig()
        self.proxies: Dict[str, Proxy] = {}
        self.alerts: List[Alert] = []
        self.active_alert: Optional[Alert] = None
        self.webhooks: List[Webhook] = []
        self.integrations: List[Integration] = []
        self.scheduler_task: Optional[asyncio.Task] = None
        self.lock: asyncio.Lock = asyncio.Lock()

        # Metrics counters
        self.total_checks: int = 0
        self.webhook_deliveries: int = 0

    def get_proxy_count(self) -> int:
        return len(self.proxies)

    def get_metrics(self) -> Metrics:
        return Metrics(
            total_checks=self.total_checks,
            active_alerts=1 if self.active_alert else 0,
            webhook_deliveries=self.webhook_deliveries,
        )
