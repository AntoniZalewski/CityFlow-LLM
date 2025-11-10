from __future__ import annotations

import asyncio
import csv
import io
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import shutil

from .config import Settings
from .models import MetricsRecord, RunInfo, SimStatePayload


@dataclass
class RunMetadata:
    run_id: str
    preset_id: str
    started_at: datetime
    steps: int
    speed_hz: int
    seed: int
    save_replay: bool
    status: str = "running"
    tags: list[str] = field(default_factory=list)
    config_path: str = ""
    run_dir: Path = field(default_factory=Path)
    generated_config_path: str = ""
    config_hash: str = ""

    def to_info(self) -> RunInfo:
        return RunInfo(
            run_id=self.run_id,
            preset_id=self.preset_id,
            started_at=self.started_at,
            steps=self.steps,
            speed_hz=self.speed_hz,
            seed=self.seed,
            save_replay=self.save_replay,
            status=self.status,
            tags=list(self.tags),
        )

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["run_dir"] = str(self.run_dir)
        return payload

    @staticmethod
    def from_json(data: dict) -> "RunMetadata":
        return RunMetadata(
            run_id=data["run_id"],
            preset_id=data["preset_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            steps=data["steps"],
            speed_hz=data["speed_hz"],
            seed=data["seed"],
            save_replay=data.get("save_replay", True),
            status=data.get("status", "completed"),
            tags=data.get("tags", []),
            config_path=data.get("config_path", ""),
            run_dir=Path(data.get("run_dir", "")),
            generated_config_path=data.get("generated_config_path", ""),
            config_hash=data.get("config_hash", ""),
        )


class RunStore:
    """Disk-backed registry for run metadata, replays and metrics."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.replays_dir = settings.data_dir / settings.replays_dirname
        self.metrics_dir = settings.data_dir / settings.metrics_dirname
        self._lock = asyncio.Lock()
        self._runs: Dict[str, RunMetadata] = {}
        self._load_existing_runs()

    def _load_existing_runs(self) -> None:
        for run_file in self.replays_dir.glob("*/run.json"):
            try:
                data = json.loads(run_file.read_text())
                meta = RunMetadata.from_json(data)
                self._runs[meta.run_id] = meta
            except Exception:
                continue

    async def create_run(
        self,
        preset_id: str,
        steps: int,
        speed_hz: int,
        seed: int,
        save_replay: bool,
        config_path: str,
    ) -> RunMetadata:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_run_id = f"{timestamp}_{preset_id}"
        run_id = base_run_id
        suffix = 1
        async with self._lock:
            while run_id in self._runs:
                run_id = f"{base_run_id}_{suffix}"
                suffix += 1
            run_dir = self.replays_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            meta = RunMetadata(
                run_id=run_id,
                preset_id=preset_id,
                started_at=datetime.utcnow(),
                steps=steps,
                speed_hz=speed_hz,
                seed=seed,
                save_replay=save_replay,
                status="running",
                config_path=config_path,
                run_dir=run_dir,
            )
            self._runs[run_id] = meta
            self._persist_metadata(meta)
            self._enforce_retention_locked()
            return meta

    async def mark_status(self, run_id: str, status: str) -> None:
        async with self._lock:
            meta = self._runs.get(run_id)
            if not meta:
                return
            meta.status = status
            self._persist_metadata(meta)

    async def attach_generated_config(self, run_id: str, generated_path: Path, config_hash: str) -> None:
        async with self._lock:
            meta = self._runs.get(run_id)
            if not meta:
                return
            meta.generated_config_path = str(generated_path)
            meta.config_hash = config_hash
            self._persist_metadata(meta)

    async def add_tag(self, run_id: str, tag: str) -> Optional[RunMetadata]:
        async with self._lock:
            meta = self._runs.get(run_id)
            if not meta:
                return None
            if tag not in meta.tags:
                meta.tags.append(tag)
                self._persist_metadata(meta)
            return meta

    async def remove_tag(self, run_id: str, tag: str) -> Optional[RunMetadata]:
        async with self._lock:
            meta = self._runs.get(run_id)
            if not meta:
                return None
            if tag in meta.tags:
                meta.tags.remove(tag)
                self._persist_metadata(meta)
            return meta

    def list_runs(self) -> list[RunInfo]:
        return [
            meta.to_info()
            for meta in sorted(self._runs.values(), key=lambda x: x.started_at, reverse=True)
        ]

    def get(self, run_id: str) -> Optional[RunMetadata]:
        return self._runs.get(run_id)

    def replay_path(self, run_id: str) -> Path:
        return self.replays_dir / run_id / "replay.ndjson"

    def metrics_path(self, run_id: str) -> Path:
        return self.metrics_dir / f"{run_id}.ndjson"

    def config_copy_path(self, run_id: str) -> Path:
        return self.replays_dir / run_id / "config.generated.json"

    def write_replay_sample(self, run_id: str, state: SimStatePayload) -> None:
        path = self.replay_path(run_id)
        payload = state.model_dump()
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload))
            fh.write("\n")

    def write_metrics_sample(self, run_id: str, state: SimStatePayload) -> MetricsRecord:
        metrics = MetricsRecord(
            t=state.t,
            vehicle_count=state.vehicle_count,
            avg_speed=state.metrics_live.avg_speed,
            avg_waiting=state.metrics_live.avg_waiting,
            throughput=state.metrics_live.throughput,
        )
        path = self.metrics_path(run_id)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(metrics.model_dump()))
            fh.write("\n")
        return metrics

    def load_metrics(self, run_id: str) -> list[MetricsRecord]:
        path = self.metrics_path(run_id)
        if not path.exists():
            return []
        records: list[MetricsRecord] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(MetricsRecord(**data))
                except Exception:
                    continue
        return records

    def load_metrics_csv(self, run_id: str) -> str:
        records = self.load_metrics(run_id)
        if not records:
            return ""
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer, fieldnames=["t", "vehicle_count", "avg_speed", "avg_waiting", "throughput"]
        )
        writer.writeheader()
        for record in records:
            writer.writerow(record.model_dump())
        return buffer.getvalue()

    def get_replay(self, run_id: str) -> list[dict]:
        path = self.replay_path(run_id)
        if not path.exists():
            return []
        frames = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    frames.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return frames

    def set_retention(self, limit: int) -> None:
        self.settings = self.settings.model_copy(update={"retention_limit": limit})

    def _persist_metadata(self, meta: RunMetadata) -> None:
        path = meta.run_dir / "run.json"
        path.write_text(json.dumps(meta.to_json(), indent=2))

    def _enforce_retention_locked(self) -> None:
        limit = self.settings.retention_limit
        if limit <= 0:
            return
        if len(self._runs) <= limit:
            return
        sorted_runs = sorted(self._runs.values(), key=lambda x: x.started_at)
        for meta in sorted_runs[:-limit]:
            run_dir = meta.run_dir
            metrics_path = self.metrics_path(meta.run_id)
            if run_dir.exists():
                shutil.rmtree(run_dir, ignore_errors=True)
            if metrics_path.exists():
                metrics_path.unlink()
            self._runs.pop(meta.run_id, None)
