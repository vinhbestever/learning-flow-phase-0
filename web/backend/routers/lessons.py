import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import student_paths

router = APIRouter(prefix="/api")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _build_question_list(qe_block: dict | None, failed_by_qid: dict) -> list:
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
            "comment_plain": q.get("comment_plain"),
            "requires_media": bool(q.get("requires_media")),
            "correct_answer": q.get("correct_answer"),
            "stem_media_urls": q.get("stem_media_urls") or [],
            "comment_media_urls": q.get("comment_media_urls") or [],
            "choice_previews": q.get("choice_previews") or [],
            "is_correct": q.get("is_correct"),
            "detail_result_id": q.get("detail_result_id"),
            "is_failed": failed is not None,
            "student_answer": failed.get("student_answer") if failed else None,
        }
        result.append(row)
    return result


@router.get("/students/{student_id}/lessons")
def get_lessons(student_id: str):
    paths = student_paths(student_id)
    p = paths["questions"]
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail=f"questions_export.json not found for student {student_id} — run export_questions.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))

    sc_data = _load_json(paths["context"])
    hw_attempted_by_lesson: dict[int, bool] = {}
    in_class_participated_by_lesson: dict[int, bool] = {}
    for l in sc_data.get("lessons") or []:
        lid = l.get("lesson_id")
        if lid is not None:
            hw_attempted_by_lesson[lid] = (l.get("homework") or {}).get("attempted", True)
            in_class_participated_by_lesson[lid] = (l.get("in_class") or {}).get("participated", False)

    return [
        {
            "lesson_id": l["lesson_id"],
            "title": l["title"],
            "level": l.get("level"),
            "position": l.get("position"),
            "last_activity_date": l.get("last_activity_date"),
            "desc": l.get("desc", ""),
            "homework_attempted": hw_attempted_by_lesson.get(l["lesson_id"]),
            "in_class_participated": in_class_participated_by_lesson.get(l["lesson_id"]),
        }
        for l in data.get("lessons", [])
    ]


@router.get("/students/{student_id}/lessons/{lesson_id}")
def get_lesson_detail(student_id: str, lesson_id: int):
    paths = student_paths(student_id)
    qe_data = _load_json(paths["questions"])
    sc_data = _load_json(paths["context"])

    qe_lesson = next(
        (l for l in qe_data.get("lessons", []) if l.get("lesson_id") == lesson_id),
        None,
    )
    sc_lesson = next(
        (l for l in sc_data.get("lessons", []) if l.get("lesson_id") == lesson_id),
        None,
    )

    if not qe_lesson and not sc_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson = qe_lesson or sc_lesson

    qe_ic = (qe_lesson or {}).get("in_class") or {}
    sc_ic = (sc_lesson or {}).get("in_class") or {}

    in_class = {
        "participated": sc_ic.get("participated", False),
        "is_completed": sc_ic.get("is_completed", False),
        "completion_pct": sc_ic.get("completion_pct"),
        "session_count": sc_ic.get("session_count", 0),
        "pronunciation_score_avg": sc_ic.get("pronunciation_score_avg"),
        "pronunciation_attempts": sc_ic.get("pronunciation_attempts", 0),
        "free_speaking_score_avg": sc_ic.get("free_speaking_score_avg"),
        "free_speaking_attempts": sc_ic.get("free_speaking_attempts", 0),
        "worst_speaking_items": sc_ic.get("worst_speaking_items") or [],
        "pronunciation_drills": qe_ic.get("pronunciation_drills") or [],
        "free_speaking_questions": qe_ic.get("free_speaking") or [],
    }

    qe_hw = (qe_lesson or {}).get("homework") or {}
    sc_hw = (sc_lesson or {}).get("homework") or {}

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
            "questions_source": block.get("questions_source"),
            "has_lms_attempt": block.get("has_lms_attempt"),
            "lms_num_question": block.get("lms_num_question"),
            "completed_lesson": block.get("completed_lesson"),
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
