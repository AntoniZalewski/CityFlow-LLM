from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import get_settings
from .models import (
    ControlResponsePayload,
    MetricsFormat,
    MetricsResponse,
    PresetListResponse,
    RetentionRequest,
    ReplaysResponse,
    RunRequestPayload,
    RunResponsePayload,
    TagRequest,
)
from .presets import list_presets
from .sim_client import SimClient
from .state_stream import StateBroadcaster, StatePoller
from .storage import RunStore

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def create_app() -> FastAPI:
    settings = get_settings()
    store = RunStore(settings)
    sim_client = SimClient(settings.sim_base_url)
    broadcaster = StateBroadcaster()
    poller = StatePoller(settings, sim_client, store, broadcaster)

    app = FastAPI(title="CityFlow API", version="0.1.0")

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - FastAPI hook
        await poller.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - FastAPI hook
        await poller.stop()
        await sim_client.close()

    @app.exception_handler(APIError)
    async def api_error_handler(_, exc: APIError) -> JSONResponse:  # pragma: no cover
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_, exc: HTTPException) -> JSONResponse:  # pragma: no cover
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("ok") is False:
            content = detail
        else:
            content = {
                "ok": False,
                "error_code": "http_error",
                "message": detail if isinstance(detail, str) else "HTTP error",
            }
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:  # pragma: no cover
        logger.exception("Unhandled API error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error_code": "internal_error",
                "message": "Unexpected server error.",
            },
        )

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "status": "healthy"}

    @app.get("/scenarios", response_model=PresetListResponse)
    async def get_scenarios() -> PresetListResponse:
        try:
            presets = list_presets(settings)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            message = detail.get("message") or str(detail) or "Preset discovery failed."
            logger.warning("Failed to list presets: %s", message)
            return PresetListResponse(ok=False, items=[], error=message)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Unexpected preset discovery error: %s", exc)
            return PresetListResponse(ok=False, items=[], error=str(exc))
        return PresetListResponse(items=sorted(presets.keys()))

    @app.post("/run", response_model=RunResponsePayload)
    async def start_run(payload: RunRequestPayload) -> RunResponsePayload:
        logger.info("Received /run payload: %s", payload.model_dump(by_alias=True, exclude_none=True))
        try:
            presets = list_presets(settings)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            raise APIError(
                exc.status_code,
                detail.get("error_code", "preset_discovery_failed"),
                detail.get("message", "Preset discovery failed."),
            ) from exc
        except Exception as exc:
            raise APIError(500, "preset_discovery_failed", f"Failed to load presets: {exc}") from exc

        preset_key = payload.preset_id or payload.id
        available_ids = sorted(presets.keys())
        if not preset_key:
            message = "preset_id (or preset) must be provided."
            if available_ids:
                message = f"{message} Available presets: {', '.join(available_ids)}"
            raise APIError(400, "preset_missing", message)

        preset = presets.get(preset_key)
        if not preset:
            message = f"Preset '{preset_key}' not found."
            if available_ids:
                message = f"{message} Available presets: {', '.join(available_ids)}"
            raise APIError(404, "preset_not_found", message)

        steps = payload.steps or preset.steps
        speed_hz = payload.speed_hz or 10
        seed = payload.seed if payload.seed is not None else preset.seed
        save_replay = preset.save_replay if payload.save_replay is None else payload.save_replay

        run_meta = await store.create_run(
            preset_id=preset.id,
            steps=steps,
            speed_hz=speed_hz,
            seed=seed,
            save_replay=save_replay,
            config_path=preset.config,
        )

        try:
            run_config_path, config_hash = _build_run_config(
                base_config=Path(preset.config),
                overrides=preset.params,
                destination=store.config_copy_path(run_meta.run_id),
                examples_dir=settings.examples_dir,
                run_dir=run_meta.run_dir,
            )
            await store.attach_generated_config(run_meta.run_id, run_config_path, config_hash)
        except FileNotFoundError as exc:
            await store.mark_status(run_meta.run_id, "error")
            raise APIError(400, "config_missing", str(exc)) from exc
        except Exception as exc:
            await store.mark_status(run_meta.run_id, "error")
            raise APIError(500, "config_build_failed", f"Failed to prepare config: {exc}") from exc

        try:
            sim_payload = {
                "run_id": run_meta.run_id,
                "config_path": str(run_config_path),
                "steps": steps,
                "speed_hz": speed_hz,
            }
            response = await sim_client.start_run(sim_payload)
        except Exception as exc:
            await store.mark_status(run_meta.run_id, "error")
            raise APIError(502, "sim_unreachable", f"Simulation backend error: {exc}") from exc

        _ensure_sim_ok(response)
        return RunResponsePayload(
            run_id=run_meta.run_id,
            preset_id=preset.id,
            started_at=run_meta.started_at,
            speed_hz=speed_hz,
        )

    @app.post("/pause", response_model=ControlResponsePayload)
    async def pause() -> ControlResponsePayload:
        state = await _forward_control(sim_client.pause)
        return state

    @app.post("/reset", response_model=ControlResponsePayload)
    async def reset() -> ControlResponsePayload:
        state = await _forward_control(sim_client.reset)
        return state

    @app.post("/resume", response_model=ControlResponsePayload)
    async def resume() -> ControlResponsePayload:
        return await _forward_control(sim_client.resume)

    @app.post("/step", response_model=ControlResponsePayload)
    async def step(n: int = Query(1, ge=1, le=10_000)) -> ControlResponsePayload:
        state = await _forward_control(lambda: sim_client.step(n))
        return state

    @app.post("/speed", response_model=ControlResponsePayload)
    async def speed(hz: int = Query(10, ge=1, le=60)) -> ControlResponsePayload:
        state = await _forward_control(lambda: sim_client.set_speed(hz))
        return state

    @app.get("/replays", response_model=ReplaysResponse)
    async def get_replays() -> ReplaysResponse:
        return ReplaysResponse(items=store.list_runs())

    @app.get("/replays/{run_id}")
    async def get_replay(run_id: str, limit: Optional[int] = Query(default=None, ge=1, le=5000)) -> dict:
        if not store.get(run_id):
            raise APIError(404, "run_not_found", f"Run '{run_id}' not found.")
        frames = store.get_replay(run_id)
        if limit:
            frames = frames[:limit]
        return {"ok": True, "run_id": run_id, "frames": frames}

    @app.get("/metrics")
    async def get_metrics(
        run_id: Optional[str] = None,
        format: MetricsFormat = Query(default="json"),
    ):
        runs = store.list_runs()
        target_run_id = run_id or (runs[0].run_id if runs else None)
        if not target_run_id:
            raise APIError(404, "no_runs", "No runs found.")
        if not store.get(target_run_id):
            raise APIError(404, "run_not_found", f"Run '{target_run_id}' not found.")
        if format == "csv":
            csv_body = store.load_metrics_csv(target_run_id)
            return PlainTextResponse(csv_body, media_type="text/csv")
        records = store.load_metrics(target_run_id)
        return MetricsResponse(ok=True, run_id=target_run_id, records=records)

    @app.post("/tags")
    async def add_tag(payload: TagRequest) -> dict:
        meta = await store.add_tag(payload.run_id, payload.tag)
        if not meta:
            raise APIError(404, "run_not_found", f"Run '{payload.run_id}' not found.")
        return {"ok": True, "run": meta.to_info()}

    @app.delete("/tags")
    async def remove_tag(payload: TagRequest) -> dict:
        meta = await store.remove_tag(payload.run_id, payload.tag)
        if not meta:
            raise APIError(404, "run_not_found", f"Run '{payload.run_id}' not found.")
        return {"ok": True, "run": meta.to_info()}

    @app.post("/retention")
    async def update_retention(payload: RetentionRequest) -> dict:
        store.set_retention(payload.limit)
        return {"ok": True, "limit": payload.limit}

    @app.get("/state")
    async def get_state_snapshot() -> dict:
        latest = broadcaster.latest()
        state = latest.model_dump() if latest else None
        return {"ok": True, "state": state}

    @app.websocket("/ws/state")
    async def ws_state(socket: WebSocket) -> None:
        await socket.accept()
        await poller.client_connected()
        queue = await broadcaster.subscribe()
        try:
            while True:
                state = await queue.get()
                await socket.send_json(state.model_dump())
        except WebSocketDisconnect:
            pass
        finally:
            await broadcaster.unsubscribe(queue)
            await poller.client_disconnected()

    async def _forward_control(
        callable_fn: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> ControlResponsePayload:
        try:
            response = await callable_fn()
        except Exception as exc:
            raise APIError(502, "sim_unreachable", str(exc)) from exc
        _ensure_sim_ok(response)
        latest = broadcaster.latest()
        status = response.get("status") or (latest.status if latest else "idle")
        t_value = response.get("t") or (latest.t if latest else 0)
        speed_value = response.get("speed_hz") or (latest.speed_hz if latest else 0)
        run_id = latest.run_id if latest else None
        return ControlResponsePayload(
            status=status,
            run_id=run_id,
            t=t_value,
            speed_hz=speed_value,
        )

    def _ensure_sim_ok(response: Dict[str, Any]) -> None:
        if isinstance(response, dict) and response.get("ok") is False:
            raise APIError(
                400,
                response.get("error_code", "sim_error"),
                response.get("message", "Simulation rejected the request."),
            )

    return app


def _build_run_config(
    base_config: Path,
    overrides: Dict[str, Any],
    destination: Path,
    examples_dir: Path,
    run_dir: Path,
) -> tuple[Path, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not base_config.exists():
        raise FileNotFoundError(f"Config file '{base_config}' does not exist.")
    with base_config.open("r", encoding="utf-8") as fh:
        config = json.load(fh)
    merged = _deep_merge(config, overrides or {})
    examples_abs = examples_dir.resolve()
    run_dir_abs = run_dir.resolve()
    run_dir_abs.mkdir(parents=True, exist_ok=True)
    merged["dir"] = str(examples_abs)
    _ensure_absolute_source_files(merged, examples_abs)
    merged["saveReplay"] = True
    merged["roadnetLogFile"] = str(run_dir_abs / "roadnet.json")
    merged["replayLogFile"] = str(run_dir_abs / "replay.txt")
    body = json.dumps(merged, indent=2)
    destination.write_text(body)
    config_hash = hashlib.sha256(json.dumps(merged, sort_keys=True).encode("utf-8")).hexdigest()
    return destination, config_hash


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    if not overrides:
        return base
    for key, value in overrides.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _ensure_absolute_source_files(config: Dict[str, Any], examples_dir: Path) -> None:
    for key in ("roadnetFile", "flowFile"):
        _ensure_absolute_file(config, key, examples_dir)


def _ensure_absolute_file(config: Dict[str, Any], key: str, base_dir: Path) -> None:
    value = config.get(key)
    if not value:
        return
    path_value = Path(value)
    if not path_value.is_absolute():
        config[key] = str((base_dir / path_value).resolve())
