import json
from pathlib import Path

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)

TEST_SID = "test_hist_1"


def _paths(d: Path) -> dict:
    return {
        "context": d / "student_context.json",
        "questions": d / "questions_export.json",
        "homework": d / "homework_assignment.json",
        "homework_by_model": d / "homework_by_model.json",
        "diagnostic": d / "diagnostic_output.txt",
    }


def test_history_returns_items(tmp_path: Path, monkeypatch) -> None:
    """Response sorted by last_activity_date descending (newest first)."""
    d = tmp_path / TEST_SID
    d.mkdir(parents=True)
    data = {
        "summary": {
            "student_id": 2102555,
            "reference_date": "2026-04-21",
        },
        "lessons": [
            {
                "lesson_id": 1,
                "title": "Unit A",
                "level": 5,
                "status": "completed",
                "last_activity_date": "2026-04-21",
                "days_since_last_practice": 3,
                "forgetting_score": 0.5,
                "weakness_score": 0.2,
                "composite_priority_score": 0.4,
                "in_class": {
                    "worst_speaking_items": [
                        {
                            "question": "Q1?",
                            "user_transcript": "A1",
                            "answer_type": "correct",
                            "score": 80,
                            "timestamp": "2026-04-10",
                        }
                    ],
                },
                "homework": {
                    "weak_skills": ["grammar"],
                    "worst_questions": [
                        {
                            "question_type": "fill",
                            "question_text": "Hello world question text here",
                            "requires_media": False,
                        }
                    ],
                },
            },
            {
                "lesson_id": 2,
                "title": "Unit B",
                "level": 4,
                "status": "completed",
                "last_activity_date": "2026-04-10",
                "days_since_last_practice": 10,
                "forgetting_score": 0.9,
                "weakness_score": 0.6,
                "composite_priority_score": 0.7,
                "in_class": {
                    "worst_speaking_items": [],
                },
                "homework": {
                    "worst_questions": [
                        {
                            "question_type": "media",
                            "question_text": "m",
                            "requires_media": True,
                        }
                    ],
                },
            },
        ],
    }
    (d / "student_context.json").write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr("web.backend.routers.history.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/history")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["student_id"] == 2102555
    assert body["count"] == 2
    assert len(body["items"]) == 2
    # 2026-04-21 > 2026-04-10
    assert body["items"][0]["lesson_id"] == 1
    assert body["items"][0]["days_since_last_practice"] == 3
    assert body["items"][0]["homework"]["failed_text_count"] == 1
    assert len(body["items"][0]["in_class"]["worst_speaking_items"]) == 1
    # second row: one media failed
    assert body["items"][1]["homework"]["failed_media_count"] == 1


def test_history_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    monkeypatch.setattr("web.backend.routers.history.student_paths", lambda _id: _paths(d))

    resp = client.get(f"/api/students/{TEST_SID}/history")
    assert resp.status_code == 404
