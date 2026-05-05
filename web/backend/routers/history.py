import json

from fastapi import APIRouter, HTTPException

from web.backend.config import student_paths

router = APIRouter(prefix="/api")


@router.get("/students/{student_id}/history")
def get_learning_history(student_id: str):
    paths = student_paths(student_id)
    p = paths["context"]
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"student_context.json not found for student {student_id} — run "
                "`python -m scripts.preprocess` (or `python preprocess.py`) from repo root"
            ),
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    summary = raw.get("summary") or {}
    lessons = raw.get("lessons") or []

    items = []
    for r in lessons:
        hw = r.get("homework") or {}
        in_class = r.get("in_class") or {}
        speaking_items = in_class.get("worst_speaking_items") or []
        worst_questions = hw.get("worst_questions") or []

        text_failed = [q for q in worst_questions if not q.get("requires_media")]
        media_failed_count = sum(1 for q in worst_questions if q.get("requires_media"))

        items.append(
            {
                "lesson_id": r.get("lesson_id"),
                "title": r.get("title"),
                "level": r.get("level"),
                "status": r.get("status"),
                "last_activity_date": r.get("last_activity_date"),
                "days_since_last_practice": r.get("days_since_last_practice"),
                "forgetting_score": r.get("forgetting_score"),
                "weakness_score": r.get("weakness_score"),
                "composite_priority_score": r.get("composite_priority_score"),
                "in_class": {
                    "participated": in_class.get("participated", False),
                    "is_completed": in_class.get("is_completed", False),
                    "completion_pct": in_class.get("completion_pct"),
                    "session_count": in_class.get("session_count", 0),
                    "pronunciation_score_avg": in_class.get("pronunciation_score_avg"),
                    "pronunciation_attempts": in_class.get("pronunciation_attempts", 0),
                    "free_speaking_score_avg": in_class.get("free_speaking_score_avg"),
                    "free_speaking_attempts": in_class.get("free_speaking_attempts", 0),
                    "conversation_score_avg": in_class.get("conversation_score_avg"),
                    "conversation_attempts": in_class.get("conversation_attempts", 0),
                    "session_metrics": in_class.get("session_metrics"),
                    "worst_speaking_items": [
                        {
                            "lms_type": w.get("lms_type"),
                            "question": (w.get("question") or "")[:200] or None,
                            "expected_answer": (w.get("expected_answer") or "")[:300] or None,
                            "user_transcript": (w.get("user_transcript") or "")[:200] or None,
                            "answer_type": w.get("answer_type"),
                            "score": w.get("score"),
                            "grammar_score": w.get("grammar_score"),
                            "pronunciation_score": w.get("pronunciation_score"),
                            "timestamp": w.get("timestamp"),
                        }
                        for w in speaking_items[:3]
                    ],
                },
                "homework": {
                    "attempted": hw.get("attempted", False),
                    "bai_tap": hw.get("bai_tap"),
                    "luyen_tap": hw.get("luyen_tap"),
                    "weak_skills": hw.get("weak_skills") or [],
                    "failed_text_count": len(text_failed),
                    "failed_media_count": media_failed_count,
                    "failed_text_questions": [
                        {
                            "question_type": q.get("question_type"),
                            "question_text": (q.get("question_text") or "")[:200],
                            "correct_answer": q.get("correct_answer"),
                            "student_answer": q.get("student_answer"),
                        }
                        for q in text_failed[:3]
                    ],
                },
            }
        )

    items.sort(key=lambda x: x.get("last_activity_date") or "", reverse=True)

    return {
        "student_id": summary.get("student_id"),
        "reference_date": summary.get("reference_date"),
        "count": len(items),
        "items": items,
    }
