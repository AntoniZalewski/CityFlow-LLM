from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", "/app/data"))
    )
    experiments_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("EXPERIMENTS_DIR", "/app/experiments"))
    )
    examples_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("EXAMPLES_DIR", "/app/examples"))
    )
    sim_base_url: str = Field(
        default_factory=lambda: os.getenv("SIM_BASE_URL", "http://cityflow-sim:7001")
    )
    state_poll_interval: float = Field(
        default_factory=lambda: float(os.getenv("STATE_POLL_INTERVAL", "2.0"))
    )
    retention_limit: int = Field(
        default_factory=lambda: int(os.getenv("RETENTION_LIMIT", "50"))
    )
    metrics_dirname: str = "metrics"
    replays_dirname: str = "replays"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / settings.replays_dirname).mkdir(parents=True, exist_ok=True)
    (settings.data_dir / settings.metrics_dirname).mkdir(parents=True, exist_ok=True)
    settings.experiments_dir.mkdir(parents=True, exist_ok=True)
    return settings
