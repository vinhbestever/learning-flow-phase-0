import json

from fastapi.testclient import TestClient

from web.backend.main import app

client = TestClient(app)


def test_get_lessons_returns_list(tmp_path, monkeypatch):
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
    f = tmp_path / "questions_export.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.lessons.QUESTIONS_EXPORT_PATH", str(f))
    resp = client.get("/api/lessons")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["lesson_id"] == 1


def test_get_lessons_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.lessons.QUESTIONS_EXPORT_PATH",
        str(tmp_path / "missing.json"),
    )
    resp = client.get("/api/lessons")
    assert resp.status_code == 404
