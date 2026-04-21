import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)


def test_get_student_returns_summary(tmp_path, monkeypatch):
    data = {
        "summary": {
            "student_id": 2102555,
            "total_lessons": 50,
            "overall_pronunciation_score_avg": 86.96,
            "overall_free_speaking_score_avg": 30.71,
            "overall_homework_skill_breakdown": {},
            "lessons_by_status": {"completed": 48},
            "overall_free_speaking_answer_type_dist": {},
            "weak_skills_global": [],
        }
    }
    f = tmp_path / "student_context.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.student.STUDENT_CONTEXT_PATH", str(f))
    resp = client.get("/api/student")
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == 2102555
    assert body["total_lessons"] == 50


def test_get_student_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.student.STUDENT_CONTEXT_PATH",
        str(tmp_path / "missing.json"),
    )
    resp = client.get("/api/student")
    assert resp.status_code == 404
