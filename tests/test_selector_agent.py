import json
from unittest.mock import MagicMock

import pytest

from agents.selector_agent import HOMEWORK_SCHEMA, build_prompt, parse_response, run_selector

DIAGNOSTIC_TEXT = "Student shows weak grammar. Struggles with subject-verb agreement."

QUESTION_POOL = [
    {
        "lesson_id": 1,
        "lesson_title": "Lesson A",
        "signal_type": "critical",
        "question_id": 1001,
        "question_folder": "Grammar",
        "question_type": "Điền vào chỗ trống",
        "question_text": "She ___ a cat.",
        "requires_media": False,
        "correct_answer": "has",
        "interaction_type": None,
    },
    {
        "lesson_id": 1,
        "lesson_title": "Lesson A",
        "signal_type": "critical",
        "question_id": None,
        "question_folder": "Speaking",
        "question_type": "free_speaking",
        "question_text": "What do you eat?",
        "requires_media": False,
        "correct_answer": None,
        "interaction_type": "free_speaking",
    },
]

VALID_HOMEWORK_ITEM = {
    "question_no": 1,
    "lesson_id": 1,
    "lesson_title": "Lesson A",
    "skill_category": "grammar",
    "question_type": "Điền vào chỗ trống",
    "question_text": "She ___ a cat.",
    "correct_answer": "has",
    "difficulty": "medium",
    "reason": "Student failed subject-verb agreement",
}


def test_build_prompt_contains_diagnostic_text():
    prompt = build_prompt(DIAGNOSTIC_TEXT, QUESTION_POOL)
    assert "subject-verb agreement" in prompt


def test_build_prompt_contains_question_pool():
    prompt = build_prompt(DIAGNOSTIC_TEXT, QUESTION_POOL)
    assert "She ___ a cat." in prompt
    assert "What do you eat?" in prompt


def test_build_prompt_contains_lesson_title():
    prompt = build_prompt(DIAGNOSTIC_TEXT, QUESTION_POOL)
    assert "Lesson A" in prompt


def test_homework_schema_has_required_fields():
    props = HOMEWORK_SCHEMA["schema"]["properties"]["homework"]["items"]["properties"]
    for field in (
        "question_no",
        "lesson_id",
        "skill_category",
        "question_text",
        "correct_answer",
        "difficulty",
        "reason",
    ):
        assert field in props, f"Missing field: {field}"


def test_parse_response_returns_list():
    raw = json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 15})
    result = parse_response(raw)
    assert isinstance(result, list)
    assert len(result) == 15


def test_parse_response_validates_count():
    raw = json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 10})
    with pytest.raises(ValueError, match="Expected 15"):
        parse_response(raw)


def test_run_selector_calls_create_with_json_schema():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 15})
                )
            )
        ]
    )
    result = run_selector(DIAGNOSTIC_TEXT, QUESTION_POOL, client=mock_client)
    assert len(result) == 15
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["temperature"] == 0
    assert "response_format" in call_kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"


def test_parse_response_rejects_none_and_empty():
    with pytest.raises((ValueError, TypeError)):
        parse_response(None)
    with pytest.raises(ValueError):
        parse_response("")
