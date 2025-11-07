from __future__ import annotations

from typing import Any, Optional

import httpx


class SimClient:
    """Small helper to interact with the private simulation service."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/run", json=payload)

    async def pause(self) -> dict[str, Any]:
        return await self._request("POST", "/pause")

    async def resume(self) -> dict[str, Any]:
        return await self._request("POST", "/resume")

    async def reset(self) -> dict[str, Any]:
        return await self._request("POST", "/reset")

    async def set_speed(self, hz: int) -> dict[str, Any]:
        return await self._request("POST", "/speed", params={"hz": hz})

    async def step(self, steps: int) -> dict[str, Any]:
        return await self._request("POST", "/step", params={"n": steps})

    async def get_state(self) -> Optional[dict[str, Any]]:
        try:
            return await self._request("GET", "/state")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}

    async def close(self) -> None:
        await self._client.aclose()
