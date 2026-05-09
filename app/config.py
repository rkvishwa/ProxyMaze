from pydantic import BaseModel, ConfigDict


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_interval_seconds: int = 30
    request_timeout_ms: int = 5000
