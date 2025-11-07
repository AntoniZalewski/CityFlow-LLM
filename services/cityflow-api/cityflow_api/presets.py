from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

import yaml
from fastapi import HTTPException
from pydantic import ValidationError

from .config import Settings
from .models import PresetModel

logger = logging.getLogger(__name__)


def list_presets(settings: Settings) -> Dict[str, PresetModel]:
    experiments_dir = settings.experiments_dir
    experiments_abs = experiments_dir.resolve()
    presets: Dict[str, PresetModel] = {}
    candidates: List[Path] = []
    for pattern in ("*.yaml", "*.yml"):
        candidates.extend(sorted(experiments_dir.glob(pattern)))
    unique_paths: List[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)
    unique_paths.sort(key=lambda p: str(p))
    logger.info(
        "Discovering presets in %s; files: %s",
        experiments_abs,
        [str(path.resolve()) for path in unique_paths],
    )
    for path in unique_paths:
        preset = _load_single(settings, path)
        presets[preset.id] = preset
    return presets


def load_preset(settings: Settings, preset_id: str) -> PresetModel:
    preset_files: List[Path] = []
    for pattern in (f"{preset_id}.yaml", f"{preset_id}.yml"):
        preset_files.extend(settings.experiments_dir.glob(pattern))
    if not preset_files:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "error_code": "preset_not_found", "message": f"Preset '{preset_id}' not found."},
        )
    return _load_single(settings, preset_files[0])


def _load_single(settings: Settings, path: Path) -> PresetModel:
    with path.open("r", encoding="utf-8", newline="") as fh:
        data = yaml.safe_load(fh) or {}
    try:
        preset = PresetModel(**data)
    except ValidationError as exc:
        errors = exc.errors()
        reason = errors[0].get("msg", str(exc)) if errors else str(exc)
        message = f"Preset file '{path.name}' is invalid: {reason}"
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error_code": "INVALID_PRESET",
                "message": message,
            },
        ) from exc
    # Ensure config path is absolute inside the container for deterministic mounts.
    config_path = Path(preset.config)
    if not config_path.is_absolute():
        base_dir = settings.examples_dir.parent
        config_path = (base_dir / preset.config).resolve()
    if not config_path.exists():
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error_code": "config_missing",
                "message": f"Config file '{preset.config}' referenced by preset '{preset.id}' is missing.",
            },
        )
    preset.config = str(config_path)
    # Normalise params to dict
    preset.params = preset.params or {}
    _validate_params(preset.params)
    return preset


def _validate_params(params: Dict) -> None:
    if not isinstance(params, dict):
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error_code": "invalid_params",
                "message": "Preset params must be a mapping.",
            },
        )
    try:
        json.dumps(params)
    except TypeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error_code": "invalid_params",
                "message": f"Preset params must be JSON serialisable: {exc}",
            },
        ) from exc
