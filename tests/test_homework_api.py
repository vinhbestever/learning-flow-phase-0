import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)


def _paths_for(d: Path) -> dict:
    return {
        "context": d / "student_context.json",
        "questions": d / "questions_export.json",
        "homework": d / "homework_assignment.json",
        "homework_by_model": d / "homework_by_model.json",
    }


def test_get_homework_returns_data(tmp_path: Path, monkeypatch) -> None:
    sid = "test_hw_1"
    d = tmp_path / sid
    d.mkdir(parents=True)
    hw = {
        "homework": [
            {
                "question_no": 1,
                "lesson_id": 100,
                "lesson_title": "T",
                "skill_category": "grammar",
                "question_type": "fill",
                "question_text": "Q",
                "correct_answer": "A",
                "difficulty": "easy",
                "reason": "R",
                "question_id": None,
                "requires_media": False,
            }
        ]
    }
    diag = "Student analysis text."
    (d / "homework_assignment.json").write_text(json.dumps(hw), encoding="utf-8")
    (d / "student_context.json").write_text(
        '{"scored_candidates":[],"lessons":[]}', encoding="utf-8"
    )
    (d / "questions_export.json").write_text('{"lessons":[]}', encoding="utf-8")
    hbm = {
        "version": 1,
        "last_run_model": "gpt-5.4",
        "models": {
            "gpt-5.4": {
                "updated_at": "2026-01-01T00:00:00+00:00",
                "diagnostic": diag,
                "homework": hw["homework"],
            }
        },
    }
    (d / "homework_by_model.json").write_text(json.dumps(hbm), encoding="utf-8")

    monkeypatch.setattr("web.backend.routers.homework.student_paths", lambda _id: _paths_for(d))

    resp = client.get(f"/api/students/{sid}/homework")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["homework"]) == 1
    assert body["diagnostic"] == diag
    assert "models" in body
    assert "last_run_model" in body
    assert "gpt-5.4" in body["models"]
    assert body["last_run_model"] == "gpt-5.4"


def test_get_homework_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    sid = "missing_hw"
    d = tmp_path / sid
    d.mkdir(parents=True)
    monkeypatch.setattr("web.backend.routers.homework.student_paths", lambda _id: _paths_for(d))

    resp = client.get(f"/api/students/{sid}/homework")
    assert resp.status_code == 404
