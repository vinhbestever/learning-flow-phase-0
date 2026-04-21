from unittest.mock import MagicMock

from agents.diagnostic_agent import build_prompt, run_diagnostic

SUMMARY = {
    "overall_pronunciation_score_avg": 86.96,
    "overall_free_speaking_score_avg": 30.71,
    "overall_free_speaking_answer_type_dist": {"correct": 48, "incorrect": 34, "inaccordant": 16},
    "total_lessons": 50,
    "lessons_by_status": {"completed": 48, "in_class_only": 2},
}

CANDIDATES = [
    {
        "lesson_id": 1,
        "title": "Lesson A",
        "signal_type": "critical",
        "days_since_last_practice": 20,
        "weakness_score": 0.79,
        "composite_priority_score": 0.89,
        "weak_skills": ["grammar"],
        "failed_text_questions": [
            {
                "question_text": "She ___ a cat.",
                "correct_answer": "has",
                "student_answer": "have",
                "question_type": "Điền vào chỗ trống",
            }
        ],
        "worst_speaking_items": [
            {
                "question": "What do you eat?",
                "user_transcript": "I eat bitter.",
                "score": 0,
                "answer_type": "inaccordant",
            }
        ],
        "usable_question_count": 8,
    },
    {
        "lesson_id": 2,
        "title": "Lesson B",
        "signal_type": "spaced_rep",
        "days_since_last_practice": 18,
        "weakness_score": 0.3,
        "composite_priority_score": 0.65,
        "weak_skills": [],
        "failed_text_questions": [],
        "worst_speaking_items": [],
        "usable_question_count": 5,
    },
]


def test_build_prompt_contains_summary_stats():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "86.96" in prompt
    assert "30.71" in prompt


def test_build_prompt_contains_lesson_titles():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "Lesson A" in prompt
    assert "Lesson B" in prompt


def test_build_prompt_labels_signal_types():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "CRITICAL" in prompt.upper() or "critical" in prompt
    assert "SPACED" in prompt.upper() or "spaced_rep" in prompt


def test_build_prompt_includes_failed_question():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "She ___ a cat." in prompt


def test_run_diagnostic_returns_string():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Student has weak grammar."))]
    )
    result = run_diagnostic(SUMMARY, CANDIDATES, client=mock_client)
    assert isinstance(result, str)
    assert len(result) > 0


def test_run_diagnostic_calls_gpt4o():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Analysis text."))]
    )
    run_diagnostic(SUMMARY, CANDIDATES, client=mock_client)
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["temperature"] == 0.4
