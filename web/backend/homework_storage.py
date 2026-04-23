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


def _ensure_shape(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    out.setdefault("version", SCHEMA_VERSION)
    out.setdefault("last_run_model", None)
    out.setdefault("models", {})
    return out


def load_homework_state(hbm_path: Path) -> dict[str, Any]:
    """
    Load homework-by-model state from ``homework_by_model.json``.

    If the file is missing or invalid, returns an empty in-memory state.
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
) -> None:
    """Merge into ``homework_by_model.json``; overwrites the entry for ``model_id`` only."""
    state = load_homework_state(hbm_path)
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
