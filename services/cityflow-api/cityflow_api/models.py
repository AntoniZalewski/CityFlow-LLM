from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    message: str


class PresetModel(BaseModel):
    id: str
    config: str
    steps: int
    seed: int
    save_replay: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)


class PresetListResponse(BaseModel):
    ok: bool = True
    items: list[str]
    error: Optional[str] = None


class RunRequestPayload(BaseModel):
    id: str = Field(..., description="Client-supplied identifier for this run request.")
    preset_id: Optional[str] = Field(
        default=None,
        alias="preset",
        description="Preset identifier; accepts both 'preset_id' and legacy 'preset' keys.",
    )
    steps: Optional[int] = Field(default=None, ge=1)
    speed_hz: Optional[int] = Field(default=None, ge=1, le=60)
    seed: Optional[int] = Field(default=None, ge=0)
    save_replay: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class RunResponsePayload(BaseModel):
    ok: bool = True
    run_id: str
    preset_id: str
    started_at: datetime
    speed_hz: int


class ControlResponsePayload(BaseModel):
    ok: bool = True
    status: Literal["idle", "running", "paused", "completed", "error"]
    run_id: Optional[str] = None
    t: int = 0
    speed_hz: int = 0


class RunInfo(BaseModel):
    run_id: str
    preset_id: str
    started_at: datetime
    steps: int
    speed_hz: int
    seed: int
    save_replay: bool
    status: str
    tags: list[str] = Field(default_factory=list)


class ReplaysResponse(BaseModel):
    ok: bool = True
    items: list[RunInfo]


class LaneSnapshot(BaseModel):
    vehicles: int = 0
    waiting: int = 0


class LiveMetrics(BaseModel):
    avg_speed: Optional[float] = None
    avg_waiting: Optional[float] = None
    throughput: Optional[float] = None


class SimStatePayload(BaseModel):
    t: int = 0
    run_id: Optional[str] = None
    status: str = "idle"
    vehicle_count: int = 0
    lanes: Dict[str, LaneSnapshot] = Field(default_factory=dict)
    signals: Dict[str, Any] = Field(default_factory=dict)
    metrics_live: LiveMetrics = Field(default_factory=LiveMetrics)
    speed_hz: int = 10
    step_limit: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MetricsRecord(BaseModel):
    t: int
    vehicle_count: int
    avg_speed: Optional[float] = None
    avg_waiting: Optional[float] = None
    throughput: Optional[float] = None


MetricsFormat = Literal["json", "csv"]


class MetricsResponse(BaseModel):
    ok: bool = True
    run_id: str
    records: list[MetricsRecord]


class TagRequest(BaseModel):
    run_id: str
    tag: str


class RetentionRequest(BaseModel):
    limit: int = Field(ge=1, le=200)
