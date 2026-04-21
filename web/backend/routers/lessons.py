import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import QUESTIONS_EXPORT_PATH as QUESTIONS_EXPORT_PATH

router = APIRouter(prefix="/api")


@router.get("/lessons")
def get_lessons():
    p = Path(QUESTIONS_EXPORT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="questions_export.json not found — run export_questions.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return [
        {
            "lesson_id": l["lesson_id"],
            "title": l["title"],
            "level": l.get("level"),
            "position": l.get("position"),
            "last_activity_date": l.get("last_activity_date"),
            "desc": l.get("desc", ""),
        }
        for l in data.get("lessons", [])
    ]
