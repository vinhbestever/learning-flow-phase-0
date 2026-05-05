def _pronunciation_phoneme_detail(result: dict | None) -> dict | None:
    """Rich IPA / per-phone scores from Digital Teacher (matches Rino post-class drill expand)."""
    if not result:
        return None
    ad = result.get("additionalData") or {}
    sp = ad.get("speaking")
    if not isinstance(sp, dict):
        return None
    inner = sp.get("result")
    if not isinstance(inner, dict) or not inner:
        return None
    return {
        "matched_transcripts_ipa": inner.get("matchedTranscriptsIpa"),
        "is_letter_correct_all_words": inner.get("isLetterCorrectAllWords"),
        "word_score_list": inner.get("wordScoreList"),
    }


def extract_pronunciation_drill(r):
    lms = r.get("lmsData") or {}
    result = r.get("result") or {}
    return {
        "interaction_type": "pronunciation_drill",
        "expected_transcript": lms.get("expectedTranscript"),
        "question_prompt": lms.get("question"),
        "user_transcript": result.get("userTranscript"),
        "pronunciation_score": result.get("pronunciationScore"),
        "overall_score": result.get("score"),
        "audio_url": result.get("audioUrl"),
        "reaction_time_ms": r.get("reactionTimeMs"),
        "pronunciation_detail": _pronunciation_phoneme_detail(result),
    }


def extract_free_speaking(r):
    """Warmup / unscripted speaking (additionalData.warmup)."""
    lms = r.get("lmsData") or {}
    result = r.get("result") or {}
    return {
        "interaction_type": "free_speaking",
        "question": lms.get("question"),
        "expected_transcript": lms.get("expectedTranscript"),
        "question_type": lms.get("questionType"),
        "target_objects": None,
        "user_transcript": result.get("userTranscript"),
        "score": result.get("score"),
        "audio_url": result.get("audioUrl"),
        "reaction_time_ms": r.get("reactionTimeMs"),
    }



def extract_conversation(r):
    lms = r.get("lmsData") or {}
    result = r.get("result") or {}
    return {
        "interaction_type": "conversation",
        "question": lms.get("question"),
        "expected_transcript": lms.get("expectedTranscript"),
        "question_type": lms.get("questionType"),
        "user_transcript": result.get("userTranscript"),
        "score": result.get("score"),
        "grammar_score": result.get("grammarScore"),
        "pronunciation_score": result.get("pronunciationScore"),
        "audio_url": result.get("audioUrl"),
        "reaction_time_ms": r.get("reactionTimeMs"),
    }


def _interactive_attempt(r: dict) -> dict:
    res = r.get("result") or {}
    return {
        "reaction_time_ms": r.get("reactionTimeMs"),
        "student_score": res.get("score"),
        "student_user_answers": res.get("userAnswers") or [],
    }


def extract_interactive(r):
    """Extract NON_AUDIO in-class exercise."""
    lms = r.get("lmsData") or {}
    qt = lms.get("questionType")
    question_text = lms.get("question") or ""
    raw_answers = lms.get("answers") or []
    attempt = _interactive_attempt(r)

    if qt == "single_choice":
        options = [
            {"id": a.get("id"), "content": a.get("content"), "is_correct": a.get("isCorrect", False)}
            for a in raw_answers
            if isinstance(a, dict)
        ]
        correct_option = next((a["content"] for a in options if a["is_correct"]), None)
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "options": options,
            "correct_answer": correct_option,
            **attempt,
        }

    if qt == "true_false":
        correct_option = next(
            (a.get("content") for a in raw_answers if isinstance(a, dict) and a.get("isCorrect")),
            None,
        )
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "correct_answer": correct_option,
            **attempt,
        }

    if qt == "fill_paragraph":
        letter_pool = [a.get("content") for a in raw_answers if isinstance(a, dict)]
        correct_word = "".join(letter_pool)
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "letter_pool": letter_pool,
            "correct_answer": correct_word,
            **attempt,
        }

    if qt == "matching":
        terms = [a.get("content") for a in raw_answers if isinstance(a, dict)]
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text or "Match the following",
            "terms": terms,
            **attempt,
        }

    return {
        "interaction_type": "interactive",
        "question_type": qt,
        "question": question_text or None,
        "requires_media": True,
        **attempt,
    }


def compute_session_metrics(sessions: list, results: list) -> dict | None:
    """Session-level stats similar to Rino post-class summary (cups, turns, reaction)."""
    if not sessions:
        return None

    def _ts(s: dict) -> str:
        for key in ("lastActiveAt", "updatedAt", "startedAt"):
            v = s.get(key)
            if isinstance(v, dict):
                d = v.get("$date") or ""
                if d:
                    return d
        return ""

    latest = max(sessions, key=_ts)
    ck = latest.get("checkpoint") or {}
    audio = [r for r in results if r.get("interactionType") == "AUDIO"]
    rts = [r["reactionTimeMs"] for r in audio if isinstance(r.get("reactionTimeMs"), (int, float))]
    return {
        "cups": ck.get("currentCups"),
        "audio_turns": len(audio),
        "avg_reaction_ms": int(round(sum(rts) / len(rts))) if rts else None,
        "fastest_reaction_ms": int(min(rts)) if rts else None,
        "total_duration_ms": latest.get("totalDurationMs"),
        "session_status": latest.get("status"),
        "completion_pct": latest.get("completionPercentage"),
    }
