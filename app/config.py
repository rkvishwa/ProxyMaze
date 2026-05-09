from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    check_interval_seconds: int = Field(default=30, gt=0)
    request_timeout_ms: int = Field(default=5000, gt=0)
