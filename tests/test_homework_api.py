import json

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)


def test_get_homework_returns_data(tmp_path, monkeypatch):
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
            }
        ]
    }
    diag = "Student analysis text."
    hw_file = tmp_path / "homework_assignment.json"
    hw_file.write_text(json.dumps(hw), encoding="utf-8")
    diag_file = tmp_path / "diagnostic_output.txt"
    diag_file.write_text(diag, encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.homework.HOMEWORK_PATH", str(hw_file))
    monkeypatch.setattr("web.backend.routers.homework.DIAGNOSTIC_PATH", str(diag_file))
    resp = client.get("/api/homework")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["homework"]) == 1
    assert body["diagnostic"] == diag


def test_get_homework_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.homework.HOMEWORK_PATH",
        str(tmp_path / "missing.json"),
    )
    monkeypatch.setattr(
        "web.backend.routers.homework.DIAGNOSTIC_PATH",
        str(tmp_path / "missing.txt"),
    )
    resp = client.get("/api/homework")
    assert resp.status_code == 404
