import asyncio
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Optional, Set, TYPE_CHECKING, TypeVar

from .config import get_settings
from .engine import EngineAdapter, EngineSnapshot
from .models import LaneState, MetricsLive, RunRequest, SimulationState

if TYPE_CHECKING:  # pragma: no cover
    from asyncio import Queue

T = TypeVar("T")


def _create_task(coro: Coroutine[Any, Any, T]) -> asyncio.Task:
    try:
        return asyncio.create_task(coro)
    except AttributeError:  # pragma: no cover - Python 3.6 fallback
        loop = asyncio.get_event_loop()
        return loop.create_task(coro)


async def _to_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    loop = asyncio.get_event_loop()
    bound = partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, bound)


class SimulationService:
    """Owns the CityFlow engine instance and ticking loop."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._engine: Optional[EngineAdapter] = None
        self._active_request: Optional[RunRequest] = None
        self._state = SimulationState()
        self._lock = asyncio.Lock()
        self._loop_task: Optional[asyncio.Task] = None
        self._subscribers: Set["Queue"] = set()
        self._subs_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._loop_task is None:
            self._loop_task = _create_task(self._loop())

    async def shutdown(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        engine = self._engine
        if engine:
            engine.close()

    async def subscribe(self) -> "Queue":
        queue: "Queue" = asyncio.Queue(maxsize=1)
        async with self._lock:
            snapshot = self._state.copy(deep=True)
        await queue.put(snapshot)
        async with self._subs_lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: "Queue") -> None:
        async with self._subs_lock:
            self._subscribers.discard(queue)

    async def start_run(self, payload: RunRequest) -> SimulationState:
        async with self._lock:
            config_path = Path(payload.config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file '{payload.config_path}' not found.")
            if self._engine:
                self._engine.close()
            self._engine = EngineAdapter(
                config_path=str(config_path),
                seed=payload.seed,
                thread_num=payload.thread_num,
            )
            self._active_request = payload
            self._state = SimulationState(
                run_id=payload.run_id,
                status="running",
                t=0,
                step_limit=payload.steps,
                speed_hz=payload.speed_hz,
                vehicle_count=0,
                lanes={},
                signals={},
                updated_at=datetime.utcnow(),
            )
            snapshot = self._state.copy(deep=True)
        await self._broadcast(snapshot)
        return snapshot

    async def pause(self) -> SimulationState:
        async with self._lock:
            if self._state.status == "running":
                self._state.status = "paused"
                self._state.updated_at = datetime.utcnow()
            snapshot = self._state.copy(deep=True)
        await self._broadcast(snapshot)
        return snapshot

    async def resume(self) -> SimulationState:
        async with self._lock:
            if self._state.run_id and self._state.status in {"paused", "completed"}:
                self._state.status = "running"
                self._state.updated_at = datetime.utcnow()
            snapshot = self._state.copy(deep=True)
        await self._broadcast(snapshot)
        return snapshot

    async def reset(self) -> SimulationState:
        async with self._lock:
            if not self._active_request:
                snapshot = self._state.copy(deep=True)
                return snapshot
            self._engine = EngineAdapter(
                config_path=self._active_request.config_path,
                seed=self._active_request.seed,
                thread_num=self._active_request.thread_num,
            )
            self._state = SimulationState(
                run_id=self._active_request.run_id,
                status="paused",
                t=0,
                step_limit=self._active_request.steps,
                speed_hz=self._active_request.speed_hz,
                vehicle_count=0,
                updated_at=datetime.utcnow(),
            )
            snapshot = self._state.copy(deep=True)
        await self._broadcast(snapshot)
        return snapshot

    async def set_speed(self, hz: int) -> SimulationState:
        hz = max(1, min(self.settings.max_speed_hz, hz))
        async with self._lock:
            self._state.speed_hz = hz
            self._state.updated_at = datetime.utcnow()
            snapshot = self._state.copy(deep=True)
        await self._broadcast(snapshot)
        return snapshot

    async def step(self, steps: int) -> SimulationState:
        engine = await self._get_engine()
        snapshot = await _to_thread(engine.step, steps)
        async with self._lock:
            self._apply_snapshot(snapshot)
            if self._state.status == "running":
                self._state.status = "paused"
            state_view = self._state.copy(deep=True)
        await self._broadcast(state_view)
        return state_view

    async def get_state(self) -> SimulationState:
        async with self._lock:
            return self._state.copy(deep=True)

    async def _broadcast(self, state: SimulationState) -> None:
        async with self._subs_lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(state)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(state)
                except asyncio.QueueFull:
                    continue

    async def _get_engine(self) -> EngineAdapter:
        async with self._lock:
            if not self._engine:
                raise RuntimeError("Engine not initialised. Start a run first.")
            return self._engine

    async def _loop(self) -> None:
        try:
            while True:
                async with self._lock:
                    engine = self._engine
                    status = self._state.status
                    speed_hz = self._state.speed_hz or self.settings.default_speed_hz
                if engine and status == "running":
                    try:
                        snapshot = await _to_thread(engine.step, 1)
                    except Exception as exc:  # pragma: no cover - defensive
                        async with self._lock:
                            self._state.status = "error"
                            self._state.message = str(exc)
                            self._state.updated_at = datetime.utcnow()
                            state_view = self._state.copy(deep=True)
                        await self._broadcast(state_view)
                        await asyncio.sleep(self.settings.idle_sleep)
                        continue
                    async with self._lock:
                        self._apply_snapshot(snapshot)
                        state_view = self._state.copy(deep=True)
                    await self._broadcast(state_view)
                    await asyncio.sleep(max(1.0 / max(1, speed_hz), 0.0))
                else:
                    await asyncio.sleep(self.settings.idle_sleep)
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            return

    def _apply_snapshot(self, snapshot: EngineSnapshot) -> None:
        self._state.t = snapshot.current_time
        self._state.vehicle_count = snapshot.vehicle_count
        lane_states: Dict[str, LaneState] = {}
        for lane_id, count in snapshot.lane_vehicle_count.items():
            waiting = snapshot.lane_waiting_vehicle_count.get(lane_id, 0)
            lane_states[lane_id] = LaneState(vehicles=count, waiting=waiting)
        self._state.lanes = lane_states
        avg_speed = None
        if snapshot.vehicle_speed:
            avg_speed = sum(snapshot.vehicle_speed.values()) / len(
                snapshot.vehicle_speed
            )
        avg_waiting = None
        if snapshot.lane_waiting_vehicle_count:
            avg_waiting = sum(snapshot.lane_waiting_vehicle_count.values()) / len(
                snapshot.lane_waiting_vehicle_count
            )
        throughput = None
        if snapshot.current_time:
            throughput = snapshot.vehicle_count / snapshot.current_time
        self._state.metrics_live = MetricsLive(
            avg_speed=avg_speed,
            avg_waiting=avg_waiting,
            throughput=throughput,
        )
        self._state.updated_at = datetime.utcnow()
        if self._state.step_limit and snapshot.current_time >= self._state.step_limit:
            self._state.status = "completed"
