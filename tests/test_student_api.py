import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)

TEST_SID = "test_stu_1"


def _paths(d: Path) -> dict:
    return {
        "context": d / "student_context.json",
        "questions": d / "questions_export.json",
        "homework": d / "homework_assignment.json",
        "homework_by_model": d / "homework_by_model.json",
        "diagnostic": d / "diagnostic_output.txt",
    }


def test_get_student_profile_returns_summary(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / TEST_SID
    d.mkdir(parents=True)
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
    (d / "student_context.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.student.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/profile")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["student_id"] == 2102555
    assert body["total_lessons"] == 50


def test_get_student_profile_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "no_ctx"
    d.mkdir()
    monkeypatch.setattr("web.backend.routers.student.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/profile")
    assert resp.status_code == 404
