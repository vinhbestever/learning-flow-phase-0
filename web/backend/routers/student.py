import json

from fastapi import APIRouter, HTTPException

from web.backend.config import list_students, student_paths

router = APIRouter(prefix="/api")


@router.get("/students")
def get_students():
    """List all students that have processed data available."""
    result = []
    for sid in list_students():
        paths = student_paths(sid)
        data = json.loads(paths["context"].read_text(encoding="utf-8"))
        summary = data.get("summary", {})
        completed = (summary.get("lessons_by_status") or {}).get("completed", 0)
        total = summary.get("total_lessons", 0)
        result.append({
            "student_id": sid,
            "total_lessons": total,
            "completed": completed,
            "completion_pct": min(100, round(completed / total * 100)) if total else 0,
            "pronunciation_avg": summary.get("overall_pronunciation_score_avg"),
            "free_speaking_avg": summary.get("overall_free_speaking_score_avg"),
        })
    return result


@router.get("/students/{student_id}/profile")
def get_student_profile(student_id: str):
    paths = student_paths(student_id)
    p = paths["context"]
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail=f"student_context.json not found for student {student_id} — run preprocess.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["summary"]
