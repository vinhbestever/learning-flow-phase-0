from __future__ import annotations

import json
from pathlib import Path


def load_data(student_id: str) -> tuple[dict, dict, dict | None]:
    base = Path("output") / student_id
    with open(base / "student_context.json", encoding="utf-8") as f:
        student_context = json.load(f)
    with open(base / "homework_by_model.json", encoding="utf-8") as f:
        homework_by_model = json.load(f)
    qe_path = base / "questions_export.json"
    questions_export = None
    if qe_path.exists():
        with open(qe_path, encoding="utf-8") as f:
            questions_export = json.load(f)
    return student_context, homework_by_model, questions_export


def build_question_id_set(questions_export: dict | None) -> set[int]:
    qids: set[int] = set()
    if not questions_export:
        return qids
    for lesson in questions_export.get("lessons", []):
        for section in ("bai_tap", "luyen_tap"):
            hw_sec = lesson.get("homework", {}).get(section, {})
            for q in hw_sec.get("questions", []):
                qid = q.get("question_id")
                if qid is not None:
                    qids.add(qid)
    return qids
