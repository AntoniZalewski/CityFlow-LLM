import os
from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration loaded from environment variables."""

    host: str = Field(default_factory=lambda: os.getenv("SIM_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("SIM_PORT", "7001")))
    default_speed_hz: int = Field(
        default_factory=lambda: int(os.getenv("SIM_DEFAULT_SPEED_HZ", "10"))
    )
    max_speed_hz: int = Field(
        default_factory=lambda: int(os.getenv("SIM_MAX_SPEED_HZ", "60"))
    )
    poll_hz: int = Field(default_factory=lambda: int(os.getenv("SIM_POLL_HZ", "20")))
    idle_sleep: float = Field(
        default_factory=lambda: float(os.getenv("SIM_IDLE_SLEEP", "0.2"))
    )


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()
