from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CheckStatus(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class ProxyCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    status: CheckStatus


class Proxy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus = CheckStatus.DOWN
    history: List[ProxyCheck] = Field(default_factory=list)

    @property
    def uptime_percentage(self) -> float:
        if not self.history:
            return 0.0
        up_count = sum(1 for check in self.history if check.status == CheckStatus.UP)
        return round((up_count / len(self.history)) * 100, 2)


class ProxyIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    urls: List[str]
    replace: bool = False


class ProxyView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus


class ProxyDetailView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    status: CheckStatus
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
    triggered_at: str
    resolved_at: Optional[str] = None


class Webhook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str


class IntegrationType(str, Enum):
    SLACK = "slack"
    DISCORD = "discord"


class Integration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: IntegrationType
    webhook_url: str


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_interval_seconds: Optional[int] = None
    request_timeout_ms: Optional[int] = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "ok"


class Metrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_checks: int
    active_alerts: int
    webhook_deliveries: int


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event: str
    alert_id: str
    failure_rate: float
    timestamp: str
