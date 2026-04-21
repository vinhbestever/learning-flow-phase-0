import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import STUDENT_CONTEXT_PATH

router = APIRouter(prefix="/api")


def _latest_speaking_ts(candidate: dict) -> str | None:
    best = None
    for w in candidate.get("worst_speaking_items") or []:
        t = w.get("timestamp")
        if t and (best is None or t > best):
            best = t
    return best


@router.get("/history")
def get_learning_history():
    """Timeline từ scored_candidates — hoạt động & điểm yếu theo từng bài học."""
    p = Path(STUDENT_CONTEXT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="student_context.json not found — run preprocess.py first",
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    summary = raw.get("summary") or {}
    candidates = raw.get("scored_candidates") or []

    items = []
    for c in candidates:
        speaking_preview = []
        for w in (c.get("worst_speaking_items") or [])[:2]:
            speaking_preview.append(
                {
                    "question": (w.get("question") or "")[:160],
                    "user_transcript": (w.get("user_transcript") or "")[:120],
                    "answer_type": w.get("answer_type"),
                    "score": w.get("score"),
                    "timestamp": w.get("timestamp"),
                }
            )
        failed = c.get("failed_text_questions") or []
        failed_preview = []
        for q in failed[:1]:
            failed_preview.append(
                {
                    "question_type": q.get("question_type"),
                    "snippet": (q.get("question_text") or "")[:140],
                }
            )

        items.append(
            {
                "lesson_id": c.get("lesson_id"),
                "title": c.get("title"),
                "level": c.get("level"),
                "days_since_last_practice": c.get("days_since_last_practice"),
                "forgetting_score": c.get("forgetting_score"),
                "weakness_score": c.get("weakness_score"),
                "composite_priority_score": c.get("composite_priority_score"),
                "weak_skills": c.get("weak_skills") or [],
                "failed_text_count": len(failed),
                "failed_media_questions_count": c.get("failed_media_questions_count", 0),
                "failed_preview": failed_preview,
                "speaking_preview": speaking_preview,
                "last_speaking_activity": _latest_speaking_ts(c),
            }
        )

    # Gần đây luyện nhất trước (ít ngày từ lần cuối)
    items.sort(
        key=lambda x: (
            x.get("days_since_last_practice") is None,
            x.get("days_since_last_practice") if x.get("days_since_last_practice") is not None else 9999,
        )
    )

    return {
        "student_id": summary.get("student_id"),
        "reference_date": summary.get("reference_date"),
        "count": len(items),
        "items": items,
    }
