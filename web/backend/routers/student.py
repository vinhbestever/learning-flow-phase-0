import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from web.backend.config import STUDENT_CONTEXT_PATH as STUDENT_CONTEXT_PATH

router = APIRouter(prefix="/api")


@router.get("/student")
def get_student():
    p = Path(STUDENT_CONTEXT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="student_context.json not found — run preprocess.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["summary"]
