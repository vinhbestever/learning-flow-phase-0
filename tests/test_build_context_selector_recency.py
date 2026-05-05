"""
Tests that build_context keeps the full tiered list for the diagnostic agent
while restricting the selector question pool to lessons practiced within
MAX_SELECTOR_POOL_RECENCY_DAYS.
"""

from agents.context_builder import MAX_SELECTOR_POOL_RECENCY_DAYS, build_context

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_candidate(lesson_id: int, days_since: int | None, weakness: float = 0.7) -> dict:
    return {
        "lesson_id": lesson_id,
        "title": f"Lesson {lesson_id}",
        "level": 5,
        "homework_status": "attempted",
        "days_since_last_practice": days_since,
        "forgetting_score": 1.0,
        "weakness_score": weakness,
        "composite_priority_score": 0.9,
        "weak_skills": ["grammar"],
        "failed_text_questions": [
            {"question_id": lesson_id * 100, "student_answer": "x", "correct_answer": "y"}
        ],
        "question_bank_preview": [],
        "failed_media_questions_count": 0,
        "worst_speaking_items": [],
        "practice_ids": {"bai_tap": lesson_id, "luyen_tap": lesson_id + 1},
    }


def _make_lesson_export(lesson_id: int) -> dict:
    """Minimal export entry with ≥2 usable questions so it passes the export gate."""
    return {
        "lesson_id": lesson_id,
        "title": f"Lesson {lesson_id}",
        "in_class": {"free_speaking": []},
        "homework": {
            "bai_tap": {
                "practice_id": lesson_id * 10,
                "questions": [
                    {
                        "question_id": lesson_id * 100 + 1,
                        "question_folder": "Grammar",
                        "question_type": "Điền vào chỗ trống",
                        "question_text": f"Fill in lesson {lesson_id} Q1.",
                        "requires_media": False,
                        "correct_answer": "answer",
                    },
                    {
                        "question_id": lesson_id * 100 + 2,
                        "question_folder": "Grammar",
                        "question_type": "Điền vào chỗ trống",
                        "question_text": f"Fill in lesson {lesson_id} Q2.",
                        "requires_media": False,
                        "correct_answer": "answer",
                    },
                ],
            },
            "luyen_tap": None,
        },
    }


def _build_ctx(*candidates) -> dict:
    return {
        "summary": {},
        "lessons": [],
        "scored_candidates": list(candidates),
    }


def _build_export(*lesson_ids) -> dict:
    return {"lessons": [_make_lesson_export(lid) for lid in lesson_ids]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_old_lesson_stays_in_tiered_but_not_in_pool():
    """
    A lesson practiced 90 days ago (critical weakness) must appear in the
    tiered list for the diagnostic but NOT in the selector question pool.
    """
    old = _make_candidate(9001, days_since=90)
    recent = _make_candidate(9002, days_since=10)
    ctx = _build_ctx(old, recent)
    export = _build_export(9001, 9002)

    tiered, pool = build_context(ctx, export)

    tiered_ids = {c["lesson_id"] for c in tiered}
    pool_ids = {q["lesson_id"] for q in pool}

    assert 9001 in tiered_ids, "old critical lesson must surface in diagnostic tier"
    assert 9001 not in pool_ids, "old lesson must not appear in selector pool"
    assert 9002 in pool_ids, "recent lesson must appear in selector pool"


def test_boundary_day_60_included_in_pool():
    """A lesson at exactly 60 days should still be included in the pool."""
    at_limit = _make_candidate(8001, days_since=MAX_SELECTOR_POOL_RECENCY_DAYS)
    ctx = _build_ctx(at_limit)
    export = _build_export(8001)

    _, pool = build_context(ctx, export)

    assert 8001 in {q["lesson_id"] for q in pool}, "day-60 lesson must be included in pool"


def test_boundary_day_61_excluded_from_pool():
    """A lesson at 61 days should be excluded from the pool."""
    over_limit = _make_candidate(8002, days_since=MAX_SELECTOR_POOL_RECENCY_DAYS + 1)
    ctx = _build_ctx(over_limit)
    export = _build_export(8002)

    tiered, pool = build_context(ctx, export)

    assert 8002 in {c["lesson_id"] for c in tiered}, "day-61 lesson still surfaces in diagnostic"
    assert 8002 not in {q["lesson_id"] for q in pool}, "day-61 lesson excluded from selector pool"


def test_none_days_excluded_from_pool():
    """A candidate with days_since_last_practice=None must not appear in pool."""
    unknown = _make_candidate(7001, days_since=None)
    ctx = _build_ctx(unknown)
    export = _build_export(7001)

    _, pool = build_context(ctx, export)

    assert 7001 not in {q["lesson_id"] for q in pool}, "unknown-date lesson excluded from pool"
