import json
from collections import defaultdict
from pathlib import Path

from .config import QUESTION_BANK_FILES

REPO_ROOT = Path(__file__).resolve().parents[2]


def _question_bank_path(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for rel in QUESTION_BANK_FILES:
        p = (REPO_ROOT / rel).resolve()
        if p.is_file():
            return p
    return None


def load_practice_question_bank(path: str | None = None) -> dict:
    """
    practice_id (lms) -> [ rows compatible with extract_lms_question: content, answers, ... ]
    """
    p = _question_bank_path(path)
    if p is None:
        return {}
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return {}
    by_pid: dict = defaultdict(list)
    for row in data:
        if not isinstance(row, dict):
            continue
        pid = row.get("practice_id")
        if pid is not None:
            by_pid[pid].append(row)
    for pid, rows in by_pid.items():
        rows.sort(key=lambda x: (x.get("question_id") or 0, x.get("id") or 0))
    return dict(by_pid)


__all__ = ["REPO_ROOT", "load_practice_question_bank", "_question_bank_path"]
