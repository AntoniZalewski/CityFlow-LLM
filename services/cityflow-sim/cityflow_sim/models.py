from datetime import datetime
from typing import Dict, Optional

from typing_extensions import Literal
from pydantic import BaseModel, Field, validator


class RunRequest(BaseModel):
    run_id: str
    config_path: str
    steps: int = Field(ge=1)
    seed: int = Field(default=0, ge=0)
    speed_hz: int = Field(default=10, ge=1, le=60)
    thread_num: int = Field(default=1, ge=1, le=16)

    @validator("config_path")
    def config_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("config_path is required")
        return value

    @validator("run_id")
    def run_id_required(cls, value: str) -> str:
        if not value:
            raise ValueError("run_id is required")
        return value


class RunResponse(BaseModel):
    ok: bool = True
    run_id: str
    accepted_at: datetime


class ControlResponse(BaseModel):
    ok: bool = True
    status: Literal["running", "paused", "idle", "completed"]
    speed_hz: int
    t: int


class LaneState(BaseModel):
    vehicles: int = 0
    waiting: int = 0


class MetricsLive(BaseModel):
    avg_speed: Optional[float] = None
    avg_waiting: Optional[float] = None
    throughput: Optional[float] = None


class SimulationState(BaseModel):
    run_id: Optional[str] = None
    status: Literal["idle", "running", "paused", "completed", "error"] = "idle"
    t: int = 0
    step_limit: Optional[int] = None
    speed_hz: int = 10
    vehicle_count: int = 0
    lanes: Dict[str, LaneState] = Field(default_factory=dict)
    signals: Dict[str, str] = Field(default_factory=dict)
    metrics_live: MetricsLive = Field(default_factory=MetricsLive)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = None


class StateResponse(BaseModel):
    ok: bool = True
    state: SimulationState


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    message: str
