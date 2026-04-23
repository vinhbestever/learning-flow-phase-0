"""
Persistent state for homework generated per model_id (one latest run per model).

See docs/plans/2026-04-23-homework-multi-model-design.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_LEGACY_MODEL_ID = "gpt-4o"


def _ensure_shape(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    out.setdefault("version", SCHEMA_VERSION)
    out.setdefault("last_run_model", None)
    out.setdefault("models", {})
    return out


def _legacy_updated_at(legacy_hw: Path, legacy_diag: Path) -> str:
    ts = max(legacy_hw.stat().st_mtime, legacy_diag.stat().st_mtime)
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def load_homework_state(
    hbm_path: Path,
    *,
    legacy_hw_path: Path | None = None,
    legacy_diag_path: Path | None = None,
) -> dict[str, Any]:
    """
    Load merged homework-by-model state. If ``homework_by_model.json`` exists, it wins.
    Otherwise, if both legacy files exist, return an in-memory migration (not written).
    """
    if hbm_path.exists():
        raw = json.loads(hbm_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {
                "version": SCHEMA_VERSION,
                "last_run_model": None,
                "models": {},
            }
        return _ensure_shape(raw)

    if (
        legacy_hw_path is not None
        and legacy_diag_path is not None
        and legacy_hw_path.exists()
        and legacy_diag_path.exists()
    ):
        hw = json.loads(legacy_hw_path.read_text(encoding="utf-8"))
        diag = legacy_diag_path.read_text(encoding="utf-8")
        homework = hw.get("homework", [])
        if not isinstance(homework, list):
            homework = []
        return {
            "version": SCHEMA_VERSION,
            "last_run_model": DEFAULT_LEGACY_MODEL_ID,
            "models": {
                DEFAULT_LEGACY_MODEL_ID: {
                    "updated_at": _legacy_updated_at(legacy_hw_path, legacy_diag_path),
                    "diagnostic": diag,
                    "homework": homework,
                }
            },
        }

    return {
        "version": SCHEMA_VERSION,
        "last_run_model": None,
        "models": {},
    }


def save_model_result(
    hbm_path: Path,
    model_id: str,
    diagnostic: str,
    homework: list,
    *,
    legacy_hw_path: Path | None = None,
    legacy_diag_path: Path | None = None,
) -> None:
    """Merge into ``homework_by_model.json``; overwrites the entry for ``model_id`` only."""
    state = load_homework_state(
        hbm_path,
        legacy_hw_path=legacy_hw_path,
        legacy_diag_path=legacy_diag_path,
    )
    now = datetime.now(timezone.utc).isoformat()
    models = state.setdefault("models", {})
    models[model_id] = {
        "updated_at": now,
        "diagnostic": diagnostic,
        "homework": homework,
    }
    state["last_run_model"] = model_id
    state["version"] = state.get("version") or SCHEMA_VERSION
    hbm_path.parent.mkdir(parents=True, exist_ok=True)
    hbm_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
