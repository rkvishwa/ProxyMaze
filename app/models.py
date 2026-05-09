from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CheckStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    PENDING = "pending"


class ProxyCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    checked_at: str
    status: CheckStatus


class Proxy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus = CheckStatus.PENDING
    history: List[ProxyCheck] = Field(default_factory=list)
    consecutive_failures: int = 0
    last_checked_at: Optional[str] = None

    @property
    def uptime_percentage(self) -> float:
        if not self.history:
            return 0.0
        up_count = sum(1 for check in self.history if check.status == CheckStatus.UP)
        return round((up_count / len(self.history)) * 100, 2)

    @property
    def total_checks(self) -> int:
        return len(self.history)


class ProxyIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    proxies: List[str]
    replace: bool = False


class ProxyView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus
    last_checked_at: Optional[str] = None
    consecutive_failures: int = 0


class ProxyDetailView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus
    last_checked_at: Optional[str] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    uptime_percentage: float
    history: List[ProxyCheck]


class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"


class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alert_id: str
    status: AlertStatus
    failure_rate: float
    total_proxies: int
    failed_proxies: int
    failed_proxy_ids: List[str]
    threshold: float = 0.2
    fired_at: str
    resolved_at: Optional[str] = None
    message: str


class Webhook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    webhook_id: str
    url: str


class WebhookIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str


class IntegrationType(str, Enum):
    SLACK = "slack"
    DISCORD = "discord"


class Integration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: IntegrationType
    webhook_url: str
    username: str = "ProxyWatch"
    events: List[str] = Field(default_factory=lambda: ["alert.fired", "alert.resolved"])


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_interval_seconds: Optional[int] = Field(default=None, gt=0)
    request_timeout_ms: Optional[int] = Field(default=None, gt=0)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "ok"


class Metrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_checks: int
    current_pool_size: int
    active_alerts: int
    total_alerts: int
    webhook_deliveries: int
