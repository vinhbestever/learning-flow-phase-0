from agents.context_builder import build_question_pool, tier_candidates

CANDIDATE_CRITICAL = {
    "lesson_id": 1,
    "title": "Lesson A",
    "level": 5,
    "days_since_last_practice": 20,
    "forgetting_score": 1.0,
    "weakness_score": 0.6,
    "composite_priority_score": 0.8,
    "weak_skills": ["grammar"],
    "failed_text_questions": [],
    "worst_speaking_items": [],
    "practice_ids": {"bai_tap": None, "luyen_tap": 101},
}
CANDIDATE_SPACED = {
    **CANDIDATE_CRITICAL,
    "lesson_id": 2,
    "title": "Lesson B",
    "weakness_score": 0.3,
    "composite_priority_score": 0.65,
    "days_since_last_practice": 16,
}
CANDIDATE_MAINTENANCE = {
    **CANDIDATE_CRITICAL,
    "lesson_id": 3,
    "title": "Lesson C",
    "weakness_score": 0.2,
    "composite_priority_score": 0.4,
    "days_since_last_practice": 10,
}

QUESTIONS_EXPORT = {
    "lessons": [
        {
            "lesson_id": 1,
            "title": "Lesson A",
            "in_class": {
                "free_speaking": [
                    {
                        "interaction_type": "free_speaking",
                        "question": "What do you eat?",
                        "question_type": "speaking_unscripted",
                    }
                ]
            },
            "homework": {
                "bai_tap": None,
                "luyen_tap": {
                    "practice_id": 101,
                    "score": 0.8,
                    "correct": 8,
                    "total": 10,
                    "questions": [
                        {
                            "question_id": 1001,
                            "question_folder": "Grammar",
                            "question_type": "Điền vào chỗ trống",
                            "question_text": "She ___ a cat.",
                            "requires_media": False,
                            "correct_answer": "has",
                        },
                        {
                            "question_id": 1002,
                            "question_folder": "Grammar",
                            "question_type": "Một lựa chọn",
                            "question_text": None,
                            "requires_media": True,
                            "correct_answer": "blue",
                        },
                    ],
                },
            },
        },
        {
            "lesson_id": 2,
            "title": "Lesson B",
            "in_class": {"free_speaking": []},
            "homework": {
                "bai_tap": {
                    "practice_id": 201,
                    "score": 0.9,
                    "correct": 9,
                    "total": 10,
                    "questions": [
                        {
                            "question_id": 2001,
                            "question_folder": "Vocabulary",
                            "question_type": "Điền vào chỗ trống",
                            "question_text": "A dog is an ___.",
                            "requires_media": False,
                            "correct_answer": "animal",
                        },
                    ],
                },
                "luyen_tap": None,
            },
        },
        {
            "lesson_id": 3,
            "title": "Lesson C",
            "in_class": {"free_speaking": []},
            "homework": {"bai_tap": None, "luyen_tap": None},
        },
    ]
}


def test_tier_candidates_labels():
    candidates = [CANDIDATE_CRITICAL, CANDIDATE_SPACED, CANDIDATE_MAINTENANCE]
    tiered = tier_candidates(candidates)
    by_id = {c["lesson_id"]: c for c in tiered}
    assert by_id[1]["signal_type"] == "critical"
    assert by_id[2]["signal_type"] == "spaced_rep"
    assert by_id[3]["signal_type"] == "maintenance"


def test_tier_candidates_excludes_zero_question_lessons():
    candidates = [CANDIDATE_CRITICAL, CANDIDATE_MAINTENANCE]
    tiered = tier_candidates(candidates, questions_export=QUESTIONS_EXPORT, min_questions=2)
    ids = [c["lesson_id"] for c in tiered]
    # lesson 3 has 0 usable questions — excluded
    assert 3 not in ids
    assert 1 in ids


def test_tier_candidates_caps_at_15():
    many = [
        {**CANDIDATE_CRITICAL, "lesson_id": i, "composite_priority_score": 0.9 - i * 0.01}
        for i in range(1, 25)
    ]
    tiered = tier_candidates(many)
    assert len(tiered) <= 15


def test_build_question_pool_includes_media_with_stub_text():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    media_rows = [q for q in pool if q.get("question_id") == 1002]
    assert len(media_rows) == 1
    assert media_rows[0].get("requires_media") is True
    assert (media_rows[0].get("question_text") or "").strip()
    # question_id 1001 should still be present
    assert any(q["question_id"] == 1001 for q in pool)


def test_build_question_pool_includes_free_speaking():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    assert any(q.get("interaction_type") == "free_speaking" for q in pool)


def test_build_question_pool_attaches_lesson_metadata():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    for q in pool:
        assert "lesson_id" in q
        assert "lesson_title" in q
        assert "signal_type" in q


def test_tier_candidates_attaches_skill_coverage():
    candidates = [CANDIDATE_CRITICAL]
    tiered = tier_candidates(candidates)
    assert "skill_coverage" in tiered[0]
    assert isinstance(tiered[0]["skill_coverage"], list)


def test_tier_candidates_diversity_boost_is_greedy():
    # Two critical lessons share skill "grammar". A third has skill "speaking".
    # Without greedy re-scoring, both grammar lessons get the boost before selection.
    # With greedy re-scoring, the second grammar lesson loses the boost after the first
    # is selected — allowing the speaking lesson to be picked instead if scores are close.
    shared_skill_a = {
        **CANDIDATE_CRITICAL, "lesson_id": 10, "weak_skills": ["grammar"],
        "composite_priority_score": 0.80,
    }
    shared_skill_b = {
        **CANDIDATE_CRITICAL, "lesson_id": 11, "weak_skills": ["grammar"],
        "composite_priority_score": 0.75,
    }
    new_skill_c = {
        **CANDIDATE_CRITICAL, "lesson_id": 12, "weak_skills": ["speaking"],
        "composite_priority_score": 0.74,  # lower base, but brings new skill
    }
    tiered = tier_candidates([shared_skill_a, shared_skill_b, new_skill_c], max_candidates=3)
    ids = [c["lesson_id"] for c in tiered]
    # lesson 10 selected first (highest score + grammar boost)
    assert ids[0] == 10
    # lesson 12 should be picked second: after 10 is selected, "grammar" is covered,
    # so 11's adjusted score drops to 0.75 while 12 gets boost → 0.74 + 0.1 = 0.84
    assert ids[1] == 12
