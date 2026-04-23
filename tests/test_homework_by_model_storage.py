import json
from pathlib import Path

from web.backend.homework_storage import load_homework_state, save_model_result


def test_load_empty_returns_empty_models(tmp_path: Path) -> None:
    hbm = tmp_path / "homework_by_model.json"
    state = load_homework_state(hbm)
    assert state["models"] == {}
    assert state["last_run_model"] is None
    assert state.get("version") == 1


def test_legacy_files_ignored_without_hbm(tmp_path: Path) -> None:
    """Có ``homework_assignment`` (không có hbm) — không tự tạo model id."""
    hw_p = tmp_path / "homework_assignment.json"
    hw_p.write_text(
        json.dumps(
            {
                "homework": [
                    {
                        "question_no": 1,
                        "lesson_id": 1,
                        "lesson_title": "L1",
                        "skill_category": "grammar",
                        "question_type": "mc",
                        "question_text": "Q?",
                        "correct_answer": "A",
                        "difficulty": "easy",
                        "reason": "r",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    hbm = tmp_path / "homework_by_model.json"
    state = load_homework_state(hbm)
    assert state["models"] == {}
    assert state["last_run_model"] is None


def test_hbm_file_loads_when_present(tmp_path: Path) -> None:
    hbm = tmp_path / "homework_by_model.json"
    hbm.write_text(
        json.dumps(
            {
                "version": 1,
                "last_run_model": "gpt-4.1",
                "models": {
                    "gpt-4.1": {
                        "updated_at": "2026-01-01T00:00:00+00:00",
                        "diagnostic": "from hbm",
                        "homework": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    hw_p = tmp_path / "homework_assignment.json"
    hw_p.write_text('{"homework": [{"question_no": 9}]}', encoding="utf-8")

    state = load_homework_state(hbm)
    assert "gpt-4.1" in state["models"]
    assert state["models"]["gpt-4.1"]["diagnostic"] == "from hbm"
    assert state["last_run_model"] == "gpt-4.1"


def test_save_model_result_merges_and_sets_last(tmp_path: Path) -> None:
    hbm = tmp_path / "homework_by_model.json"
    save_model_result(
        hbm,
        "gpt-4.1",
        "diag a",
        [{"n": 1}],
    )
    state1 = json.loads(hbm.read_text(encoding="utf-8"))
    assert list(state1["models"].keys()) == ["gpt-4.1"]
    assert state1["last_run_model"] == "gpt-4.1"

    save_model_result(
        hbm,
        "gemini-2.5-flash",
        "diag b",
        [{"n": 2}],
    )
    state2 = json.loads(hbm.read_text(encoding="utf-8"))
    assert set(state2["models"].keys()) == {"gpt-4.1", "gemini-2.5-flash"}
    assert state2["last_run_model"] == "gemini-2.5-flash"
    assert state2["models"]["gpt-4.1"]["diagnostic"] == "diag a"
