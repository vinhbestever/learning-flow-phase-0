from unittest.mock import MagicMock

from agents.diagnostic_agent import build_prompt, run_diagnostic

SUMMARY = {
    "overall_pronunciation_score_avg": 86.96,
    "overall_free_speaking_score_avg": 30.71,
    "overall_conversation_score_avg": 86.26,
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
                "lms_type": "free_speaking",
                "question": "What do you eat?",
                "expected_answer": None,
                "user_transcript": "I eat bitter.",
                "score": 0,
                "answer_type": "inaccordant",
                "pronunciation_score": None,
                "grammar_score": None,
                "timestamp": "2026-03-01",
            },
            {
                "lms_type": "conversation",
                "question": "How do you go there usually?",
                "expected_answer": "I usually walk. Sometimes I go by bus.",
                "user_transcript": "No, I'm ready.",
                "score": 66,
                "answer_type": None,
                "pronunciation_score": 91,
                "grammar_score": 41,
                "timestamp": "2026-03-03",
            },
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
    assert "86.26" in prompt  # conversation_avg
    assert "warmup" in prompt


def test_build_prompt_formats_conversation_speaking_item():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "[conversation]" in prompt
    assert "gram=41" in prompt
    assert "pron=91" in prompt


def test_build_prompt_formats_free_speaking_item():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "[free_speaking]" in prompt
    assert "inaccordant" in prompt
    assert "warmup" in prompt



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


def test_run_diagnostic_uses_default_model():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Analysis text."))]
    )
    run_diagnostic(SUMMARY, CANDIDATES, client=mock_client)
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-5.4"
    assert call_kwargs["temperature"] == 0.4


def test_run_diagnostic_respects_model_parameter():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Analysis text."))]
    )
    run_diagnostic(SUMMARY, CANDIDATES, client=mock_client, model="gpt-4.1")
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4.1"
