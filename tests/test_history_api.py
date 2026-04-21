import json

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)


def test_history_returns_items(tmp_path, monkeypatch):
    data = {
        "summary": {
            "student_id": 2102555,
            "reference_date": "2026-04-21",
        },
        "scored_candidates": [
            {
                "lesson_id": 1,
                "title": "Unit A",
                "level": 5,
                "days_since_last_practice": 3,
                "forgetting_score": 0.5,
                "weakness_score": 0.2,
                "composite_priority_score": 0.4,
                "weak_skills": ["grammar"],
                "failed_text_questions": [
                    {
                        "question_type": "fill",
                        "question_text": "Hello world question text here",
                    }
                ],
                "failed_media_questions_count": 0,
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
            {
                "lesson_id": 2,
                "title": "Unit B",
                "level": 4,
                "days_since_last_practice": 10,
                "forgetting_score": 0.9,
                "weakness_score": 0.6,
                "composite_priority_score": 0.7,
                "weak_skills": [],
                "failed_text_questions": [],
                "failed_media_questions_count": 1,
                "worst_speaking_items": [],
            },
        ],
    }
    f = tmp_path / "student_context.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.history.STUDENT_CONTEXT_PATH", str(f))
    resp = client.get("/api/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == 2102555
    assert body["count"] == 2
    assert len(body["items"]) == 2
    # sorted by days_since ascending: 3 then 10
    assert body["items"][0]["lesson_id"] == 1
    assert body["items"][0]["days_since_last_practice"] == 3
    assert body["items"][0]["failed_text_count"] == 1
    assert len(body["items"][0]["speaking_preview"]) == 1


def test_history_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.history.STUDENT_CONTEXT_PATH",
        str(tmp_path / "missing.json"),
    )
    resp = client.get("/api/history")
    assert resp.status_code == 404
