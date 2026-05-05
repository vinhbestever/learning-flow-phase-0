import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)

TEST_SID = "test_les_1"


def _paths(d: Path) -> dict:
    return {
        "context": d / "student_context.json",
        "questions": d / "questions_export.json",
        "homework": d / "homework_assignment.json",
        "homework_by_model": d / "homework_by_model.json",
    }


def test_get_lessons_returns_list(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / TEST_SID
    d.mkdir(parents=True)
    data = {
        "lessons": [
            {
                "lesson_id": 1,
                "title": "Unit 1",
                "level": 5,
                "last_activity_date": "2026-04-15",
                "position": 1,
                "desc": "desc",
            },
            {
                "lesson_id": 2,
                "title": "Unit 2",
                "level": 4,
                "last_activity_date": "2026-04-10",
                "position": 2,
                "desc": "",
            },
        ]
    }
    (d / "questions_export.json").write_text(json.dumps(data), encoding="utf-8")
    (d / "student_context.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.lessons.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/lessons")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert body[0]["lesson_id"] == 1


def test_get_lessons_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "nope"
    d.mkdir()
    monkeypatch.setattr("web.backend.routers.lessons.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/lessons")
    assert resp.status_code == 404


def test_get_lesson_detail(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / TEST_SID
    d.mkdir(parents=True)
    data = {
        "lessons": [
            {
                "lesson_id": 42,
                "title": "Unit A - Lesson 1",
                "level": 5,
                "position": 1,
                "desc": "d",
                "last_activity_date": "2026-04-01",
                "in_class": {
                    "pronunciation_drills": [{"interaction_type": "pronunciation_drill"}],
                    "free_speaking": [],
                    "interactive": [],
                },
                "homework": {
                    "bai_tap": {
                        "practice_id": 1,
                        "score": 0.8,
                        "correct": 8,
                        "total": 10,
                        "submitted_date": "2026-04-02",
                        "questions": [
                            {
                                "question_id": 100,
                                "question_folder": "F",
                                "question_type": "fill",
                                "question_text": "Q1",
                                "requires_media": False,
                                "correct_answer": "a",
                            }
                        ],
                    },
                    "luyen_tap": None,
                },
            }
        ]
    }
    (d / "questions_export.json").write_text(json.dumps(data), encoding="utf-8")
    (d / "student_context.json").write_text('{"lessons":[]}', encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.lessons.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/lessons/42")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lesson_id"] == 42
    assert body["homework"]["bai_tap"]["total"] == 10
    assert len(body["homework"]["bai_tap"]["questions"]) == 1
    assert len(body["in_class"]["pronunciation_drills"]) == 1
    assert "brainstorm_questions" not in body["in_class"]


def test_get_lesson_detail_404(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / TEST_SID
    d.mkdir(parents=True)
    data = {"lessons": [{"lesson_id": 1, "title": "T", "homework": {}}]}
    (d / "questions_export.json").write_text(json.dumps(data), encoding="utf-8")
    (d / "student_context.json").write_text('{"lessons":[]}', encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.lessons.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/lessons/999")
    assert resp.status_code == 404
