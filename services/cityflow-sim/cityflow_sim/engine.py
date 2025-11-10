from dataclasses import dataclass
from typing import Dict, Optional

try:
    import cityflow  # type: ignore
except ImportError as exc:  # pragma: no cover - fail fast during boot
    cityflow = None
    CITYFLOW_IMPORT_ERROR = exc
else:  # pragma: no cover - import success path
    CITYFLOW_IMPORT_ERROR = None


@dataclass
class EngineSnapshot:
    current_time: int
    vehicle_count: int
    lane_vehicle_count: Dict[str, int]
    lane_waiting_vehicle_count: Dict[str, int]
    vehicle_speed: Dict[str, float]
    average_travel_time: Optional[float]


class EngineAdapter:
    """Thin wrapper around the native cityflow.Engine bindings."""

    def __init__(self, config_path: str, seed: int = 0, thread_num: int = 1):
        self.config_path = config_path
        self.seed = seed
        self.thread_num = thread_num
        self._engine = self._build_engine()

    def _build_engine(self):
        if cityflow is None:
            message = "CityFlow Python bindings are not installed inside the simulator image."
            raise RuntimeError(message) from CITYFLOW_IMPORT_ERROR
        return cityflow.Engine(
            config_file=self.config_path,
            thread_num=self.thread_num,
        )

    def reset(self) -> None:
        self.close()
        self._engine = self._build_engine()

    def close(self) -> None:
        engine = getattr(self, "_engine", None)
        if engine is None:
            return
        close = getattr(engine, "close", None)
        if callable(close):
            close()

    def step(self, steps: int = 1) -> EngineSnapshot:
        for _ in range(steps):
            self._engine.next_step()
        return self.snapshot()

    def snapshot(self) -> EngineSnapshot:
        vehicle_speed: Dict[str, float] = {}
        getter_speed = getattr(self._engine, "get_vehicle_speed", None)
        if callable(getter_speed):
            try:
                vehicle_speed = getter_speed()
            except Exception:  # pragma: no cover - defensive against bindings regressions
                vehicle_speed = {}
        average_travel_time = None
        getter_avg = getattr(self._engine, "get_average_travel_time", None)
        if callable(getter_avg):
            try:
                average_travel_time = float(getter_avg())
            except Exception:
                average_travel_time = None
        return EngineSnapshot(
            current_time=int(self._engine.get_current_time()),
            vehicle_count=int(self._engine.get_vehicle_count()),
            lane_vehicle_count=dict(self._engine.get_lane_vehicle_count()),
            lane_waiting_vehicle_count=dict(self._engine.get_lane_waiting_vehicle_count()),
            vehicle_speed=vehicle_speed,
            average_travel_time=average_travel_time,
        )
