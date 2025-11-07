from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import ValidationError
from websockets.client import connect as ws_connect

from .config import Settings
from .models import SimStatePayload
from .sim_client import SimClient
from .storage import RunStore


logger = logging.getLogger(__name__)


class StateBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[SimStatePayload]] = set()
        self._lock = asyncio.Lock()
        self._last_state: Optional[SimStatePayload] = None

    async def subscribe(self) -> asyncio.Queue[SimStatePayload]:
        queue: asyncio.Queue[SimStatePayload] = asyncio.Queue(maxsize=1)
        async with self._lock:
            self._subscribers.add(queue)
            last_state = self._last_state
        if last_state:
            await queue.put(last_state)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[SimStatePayload]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, state: SimStatePayload) -> None:
        async with self._lock:
            self._last_state = state
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

    def latest(self) -> Optional[SimStatePayload]:
        return self._last_state


class StatePoller:
    def __init__(
        self,
        settings: Settings,
        sim_client: SimClient,
        store: RunStore,
        broadcaster: StateBroadcaster,
    ) -> None:
        self.settings = settings
        self.sim_client = sim_client
        self.store = store
        self.broadcaster = broadcaster
        self._ws_task: Optional[asyncio.Task[None]] = None
        self._fallback_task: Optional[asyncio.Task[None]] = None
        self._ws_url = self._build_ws_url(settings.sim_base_url)
        self._last_state_at: float = 0.0
        self._active_clients = 0
        self._clients_lock = asyncio.Lock()
        self._ws_connected = False

    async def start(self) -> None:
        if self._ws_task is None:
            self._ws_task = asyncio.create_task(self._run_ws())
        if self._fallback_task is None:
            self._fallback_task = asyncio.create_task(self._run_http_fallback())

    async def stop(self) -> None:
        for task in (self._ws_task, self._fallback_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._ws_task = None
        self._fallback_task = None

    async def client_connected(self) -> None:
        async with self._clients_lock:
            self._active_clients += 1

    async def client_disconnected(self) -> None:
        async with self._clients_lock:
            if self._active_clients > 0:
                self._active_clients -= 1

    async def _run_ws(self) -> None:
        backoff = 1.0
        try:
            while True:
                try:
                    async with ws_connect(self._ws_url, ping_interval=20, ping_timeout=20) as socket:
                        self._set_ws_connected(True)
                        logger.info("Connected to simulator state stream at %s", self._ws_url)
                        backoff = 1.0
                        async for message in socket:
                            await self._ingest_payload(message)
                except asyncio.CancelledError:  # pragma: no cover - shutdown path
                    raise
                except Exception as exc:
                    self._set_ws_connected(False)
                    logger.warning("State WebSocket disconnected (%s): %s", self._ws_url, exc)
                    await asyncio.sleep(min(backoff, 15.0))
                    backoff = min(backoff * 2, 60.0)
                finally:
                    self._set_ws_connected(False)
        except asyncio.CancelledError:  # pragma: no cover - shutdown
            return

    async def _run_http_fallback(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.settings.state_poll_interval)
                if not self._should_poll_http():
                    continue
                try:
                    payload = await self.sim_client.get_state()
                except httpx.HTTPError as exc:
                    logger.debug("HTTP fallback failed: %s", exc)
                    continue
                if not payload:
                    continue
                await self._ingest_payload(payload)
        except asyncio.CancelledError:  # pragma: no cover
            return

    def _should_poll_http(self) -> bool:
        if self._active_clients == 0 or self._ws_connected:
            return False
        loop = asyncio.get_running_loop()
        return (loop.time() - self._last_state_at) >= self.settings.state_poll_interval

    async def _ingest_payload(self, payload: Any) -> None:
        data = payload
        if isinstance(payload, (bytes, str)):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.debug("Dropping malformed state payload: %s", payload)
                return
        if not isinstance(data, dict):
            return
        state_raw = data.get("state") or data
        if not isinstance(state_raw, dict):
            return
        await self._process_state(state_raw)

    async def _process_state(self, state_raw: dict[str, Any]) -> None:
        try:
            state = SimStatePayload(**state_raw)
        except ValidationError as exc:
            logger.warning("Invalid simulator state payload: %s", exc)
            return
        run_id = state.run_id
        if run_id:
            meta = self.store.get(run_id)
            if meta:
                try:
                    if meta.save_replay:
                        self.store.write_replay_sample(run_id, state)
                    self.store.write_metrics_sample(run_id, state)
                except Exception as exc:  # pragma: no cover - disk IO guard
                    logger.warning("Failed to persist run %s state: %s", run_id, exc)
                if state.status != meta.status:
                    await self.store.mark_status(run_id, state.status)
        await self.broadcaster.publish(state)
        self._last_state_at = asyncio.get_running_loop().time()

    @staticmethod
    def _build_ws_url(base_url: str) -> str:
        parsed = urlparse(base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        base_path = parsed.path.rstrip("/")
        full_path = f"{base_path}/ws/state" if base_path else "/ws/state"
        return urlunparse((scheme, parsed.netloc, full_path, "", "", ""))

    def _set_ws_connected(self, connected: bool) -> None:
        self._ws_connected = connected
