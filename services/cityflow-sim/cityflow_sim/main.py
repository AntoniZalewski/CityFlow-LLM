from datetime import datetime
from typing import Dict
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from .config import get_settings
from .models import (
    ControlResponse,
    ErrorResponse,
    RunRequest,
    RunResponse,
    StateResponse,
)
from .service import SimulationService


def create_app() -> FastAPI:
    settings = get_settings()
    service = SimulationService()
    app = FastAPI(title="CityFlow Simulation Service", version="0.1.0")

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - FastAPI hook
        await service.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - FastAPI hook
        await service.shutdown()

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok", "service": "cityflow-sim"}

    @app.post(
        "/run",
        response_model=RunResponse,
        responses={400: {"model": ErrorResponse}},
    )
    async def start_run(payload: RunRequest) -> RunResponse:
        try:
            state = await service.start_run(payload)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return RunResponse(run_id=state.run_id or payload.run_id, accepted_at=datetime.utcnow())

    @app.post("/pause", response_model=ControlResponse)
    async def pause() -> ControlResponse:
        state = await service.pause()
        return ControlResponse(status=state.status, speed_hz=state.speed_hz, t=state.t)

    @app.post("/resume", response_model=ControlResponse)
    async def resume() -> ControlResponse:
        state = await service.resume()
        return ControlResponse(status=state.status, speed_hz=state.speed_hz, t=state.t)

    @app.post("/reset", response_model=ControlResponse)
    async def reset() -> ControlResponse:
        state = await service.reset()
        return ControlResponse(status=state.status, speed_hz=state.speed_hz, t=state.t)

    @app.post("/speed", response_model=ControlResponse)
    async def speed(hz: int = Query(default=settings.default_speed_hz, ge=1, le=settings.max_speed_hz)) -> ControlResponse:
        state = await service.set_speed(hz)
        return ControlResponse(status=state.status, speed_hz=state.speed_hz, t=state.t)

    @app.post("/step", response_model=ControlResponse)
    async def step(n: int = Query(default=1, ge=1, le=10_000)) -> ControlResponse:
        try:
            state = await service.step(n)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ControlResponse(status=state.status, speed_hz=state.speed_hz, t=state.t)

    @app.get("/state", response_model=StateResponse)
    async def state_endpoint() -> StateResponse:
        state = await service.get_state()
        return StateResponse(state=state)

    @app.websocket("/ws/state")
    async def state_stream(socket: WebSocket) -> None:
        await socket.accept()
        queue = await service.subscribe()
        try:
            while True:
                state = await queue.get()
                payload = jsonable_encoder({"state": state.dict()})
                await socket.send_json(payload)
        except WebSocketDisconnect:
            pass
        finally:
            await service.unsubscribe(queue)

    return app
