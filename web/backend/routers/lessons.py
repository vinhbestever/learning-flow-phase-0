import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import QUESTIONS_EXPORT_PATH

router = APIRouter(prefix="/api")


def _serialize_question(q: dict) -> dict:
    return {
        "question_id": q.get("question_id"),
        "question_folder": q.get("question_folder"),
        "question_type": q.get("question_type"),
        "question_text": q.get("question_text"),
        "requires_media": bool(q.get("requires_media")),
        "correct_answer": q.get("correct_answer"),
    }


def _serialize_practice(block: dict | None) -> dict | None:
    if not block:
        return None
    return {
        "practice_id": block.get("practice_id"),
        "score": block.get("score"),
        "correct": block.get("correct"),
        "total": block.get("total"),
        "submitted_date": block.get("submitted_date"),
        "questions": [_serialize_question(q) for q in block.get("questions") or []],
    }


def _in_class_summary(lesson: dict) -> dict:
    ic = lesson.get("in_class") or {}
    return {
        "pronunciation_drills": len(ic.get("pronunciation_drills") or []),
        "free_speaking": len(ic.get("free_speaking") or []),
        "interactive": len(ic.get("interactive") or []),
    }


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


@router.get("/lessons/{lesson_id}")
def get_lesson_detail(lesson_id: int):
    """Chi tiết một lesson: bài tập / luyện tập (câu hỏi) + tóm tắt hoạt động trong lớp."""
    p = Path(QUESTIONS_EXPORT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="questions_export.json not found — run export_questions.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    for lesson in data.get("lessons", []):
        if lesson.get("lesson_id") != lesson_id:
            continue
        hw = lesson.get("homework") or {}
        return {
            "lesson_id": lesson["lesson_id"],
            "title": lesson.get("title"),
            "level": lesson.get("level"),
            "position": lesson.get("position"),
            "desc": lesson.get("desc", ""),
            "last_activity_date": lesson.get("last_activity_date"),
            "program_id": lesson.get("program_id"),
            "homework": {
                "bai_tap": _serialize_practice(hw.get("bai_tap")),
                "luyen_tap": _serialize_practice(hw.get("luyen_tap")),
            },
            "in_class_summary": _in_class_summary(lesson),
        }
    raise HTTPException(status_code=404, detail="Lesson not found")
