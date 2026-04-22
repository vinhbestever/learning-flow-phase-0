import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import QUESTIONS_EXPORT_PATH, STUDENT_CONTEXT_PATH

router = APIRouter(prefix="/api")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _build_question_list(qe_block: dict | None, failed_by_qid: dict) -> list:
    """Merge questions_export question list with student_context failed answers."""
    if not qe_block:
        return []
    result = []
    for q in qe_block.get("questions") or []:
        qid = q.get("question_id")
        failed = failed_by_qid.get(qid)
        row = {
            "question_id": qid,
            "question_folder": q.get("question_folder"),
            "question_type": q.get("question_type"),
            "question_text": q.get("question_text"),
            "requires_media": bool(q.get("requires_media")),
            "correct_answer": q.get("correct_answer"),
            "is_failed": failed is not None,
            "student_answer": failed.get("student_answer") if failed else None,
        }
        result.append(row)
    return result


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
    """Chi tiết bài học: merge questions_export (nội dung câu hỏi) + student_context (kết quả)."""
    qe_data = _load_json(Path(QUESTIONS_EXPORT_PATH))
    sc_data = _load_json(Path(STUDENT_CONTEXT_PATH))

    # Tìm lesson trong questions_export
    qe_lesson = next(
        (l for l in qe_data.get("lessons", []) if l.get("lesson_id") == lesson_id),
        None,
    )
    # Tìm lesson trong student_context
    sc_lesson = next(
        (l for l in sc_data.get("lessons", []) if l.get("lesson_id") == lesson_id),
        None,
    )

    if not qe_lesson and not sc_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson = qe_lesson or sc_lesson

    # ------------------------------------------------------------------ #
    # In-class: content từ questions_export, kết quả từ student_context   #
    # ------------------------------------------------------------------ #
    qe_ic = (qe_lesson or {}).get("in_class") or {}
    sc_ic = (sc_lesson or {}).get("in_class") or {}

    in_class = {
        # Kết quả (student_context)
        "participated": sc_ic.get("participated", False),
        "is_completed": sc_ic.get("is_completed", False),
        "completion_pct": sc_ic.get("completion_pct"),
        "session_count": sc_ic.get("session_count", 0),
        "pronunciation_score_avg": sc_ic.get("pronunciation_score_avg"),
        "pronunciation_attempts": sc_ic.get("pronunciation_attempts", 0),
        "free_speaking_score_avg": sc_ic.get("free_speaking_score_avg"),
        "free_speaking_attempts": sc_ic.get("free_speaking_attempts", 0),
        "worst_speaking_items": sc_ic.get("worst_speaking_items") or [],
        # Nội dung (questions_export)
        "pronunciation_drills": qe_ic.get("pronunciation_drills") or [],
        "free_speaking_questions": qe_ic.get("free_speaking") or [],
    }

    # ------------------------------------------------------------------ #
    # Homework: questions từ qe, kết quả + answers từ sc                  #
    # ------------------------------------------------------------------ #
    qe_hw = (qe_lesson or {}).get("homework") or {}
    sc_hw = (sc_lesson or {}).get("homework") or {}

    # Map question_id → failed row (có student_answer) từ student_context
    failed_by_qid: dict = {}
    for wq in sc_hw.get("worst_questions") or []:
        qid = wq.get("question_id")
        if qid is not None:
            failed_by_qid[qid] = wq

    def _practice_block(qe_block: dict | None, sc_block: dict | None) -> dict | None:
        if not qe_block and not sc_block:
            return None
        block = qe_block or {}
        perf = sc_block or {}
        return {
            "practice_id": block.get("practice_id") or perf.get("practice_id"),
            "score": perf.get("score") if perf else block.get("score"),
            "correct": perf.get("correct") if perf else block.get("correct"),
            "total": perf.get("total") if perf else block.get("total"),
            "submitted_date": perf.get("submitted_date") if perf else block.get("submitted_date"),
            "questions": _build_question_list(block, failed_by_qid),
        }

    homework = {
        "attempted": sc_hw.get("attempted", False),
        "bai_tap": _practice_block(qe_hw.get("bai_tap"), sc_hw.get("bai_tap")),
        "luyen_tap": _practice_block(qe_hw.get("luyen_tap"), sc_hw.get("luyen_tap")),
        "weak_skills": sc_hw.get("weak_skills") or [],
        "skill_breakdown": sc_hw.get("skill_breakdown") or {},
    }

    return {
        "lesson_id": lesson["lesson_id"],
        "title": lesson.get("title"),
        "level": lesson.get("level"),
        "position": lesson.get("position"),
        "desc": lesson.get("desc", ""),
        "last_activity_date": lesson.get("last_activity_date") or sc_lesson and sc_lesson.get("last_activity_date"),
        "status": (sc_lesson or {}).get("status"),
        "in_class": in_class,
        "homework": homework,
    }
