from collections import defaultdict

from . import config
from .transform import classify_audio, extract_user_answer_type, iso_to_date, parse_mongo_date


def compute_session_metrics(sessions, results):
    """
    Session-level aggregates (Digital Teacher) — keep in sync with export_questions.compute_session_metrics.
    Used in student_context.in_class for history UI and parity with questions_export.
    """
    if not sessions:
        return None

    def _ts(s):
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


def _build_speaking_item(r, lms_type):
    """Build a worst_speaking_items entry with system and student data clearly separated."""
    result_data = r.get("result") or {}
    lms_data = r.get("lmsData") or {}
    ad = result_data.get("additionalData") or {}

    target_objects = None
    correct_objects = None
    if "brainstorm" in ad:
        bst = ad["brainstorm"]
        objs = bst.get("objects") or []
        target_objects = [o["name"] for o in objs if isinstance(o, dict) and o.get("isMain")] or None
        correct_objects = (bst.get("result") or {}).get("correctObjects") or None

    return {
        "lms_type": lms_type,
        "question": lms_data.get("question"),
        "expected_answer": lms_data.get("expectedTranscript"),
        "target_objects": target_objects,
        "user_transcript": result_data.get("userTranscript"),
        "score": result_data.get("score"),
        "answer_type": (
            extract_user_answer_type(ad) if lms_type in ("free_speaking", "brainstorm") else None
        ),
        "correct_objects": correct_objects,
        "pronunciation_score": result_data.get("pronunciationScore"),
        "grammar_score": result_data.get("grammarScore"),
        "timestamp": iso_to_date(parse_mongo_date(r.get("timestamp"))),
        "audio_url": result_data.get("audioUrl"),
        "reaction_time_ms": r.get("reactionTimeMs"),
    }


def build_dt_in_class(sessions, results):
    if not sessions:
        return {"participated": False}

    completed_sessions = [s for s in sessions if s.get("status") == "COMPLETED"]
    latest_session = max(sessions, key=lambda s: parse_mongo_date(s.get("startedAt", "")))
    latest_date = iso_to_date(parse_mongo_date(latest_session.get("startedAt")))
    max_completion = max(s.get("completionPercentage", 0) for s in sessions)

    audio_results = [r for r in results if r.get("interactionType") == "AUDIO"]

    pron_items = [r for r in audio_results if classify_audio(r) == "pronunciation_drill"]
    pron_scores = [
        r["result"]["pronunciationScore"]
        for r in pron_items
        if (r.get("result") or {}).get("pronunciationScore") is not None
    ]
    pronunciation_score_avg = round(sum(pron_scores) / len(pron_scores), 2) if pron_scores else None

    free_items = [r for r in audio_results if classify_audio(r) == "free_speaking"]
    free_scores = [
        r["result"]["score"] for r in free_items if (r.get("result") or {}).get("score") is not None
    ]
    free_speaking_score_avg = round(sum(free_scores) / len(free_scores), 2) if free_scores else None

    answer_type_dist = defaultdict(int)
    for r in free_items:
        uat = extract_user_answer_type((r.get("result") or {}).get("additionalData"))
        if uat:
            answer_type_dist[uat] += 1

    brainstorm_items = [r for r in audio_results if classify_audio(r) == "brainstorm"]
    brainstorm_scores = [
        r["result"]["score"]
        for r in brainstorm_items
        if (r.get("result") or {}).get("score") is not None
    ]
    brainstorm_score_avg = (
        round(sum(brainstorm_scores) / len(brainstorm_scores), 2) if brainstorm_scores else None
    )
    brainstorm_answer_type_dist = defaultdict(int)
    for r in brainstorm_items:
        uat = extract_user_answer_type((r.get("result") or {}).get("additionalData"))
        if uat:
            brainstorm_answer_type_dist[uat] += 1

    convo_items = [r for r in audio_results if classify_audio(r) == "conversation"]
    convo_scores = [
        r["result"]["score"] for r in convo_items if (r.get("result") or {}).get("score") is not None
    ]
    conversation_score_avg = round(sum(convo_scores) / len(convo_scores), 2) if convo_scores else None

    failed_free = [r for r in free_items if (r.get("result") or {}).get("score", 1) == 0]
    failed_brainstorm = [r for r in brainstorm_items if (r.get("result") or {}).get("score", 1) == 0]
    failed_convo = [r for r in convo_items if ((r.get("result") or {}).get("score") or 100) < 70]
    all_failed = (
        [(r, "free_speaking") for r in failed_free]
        + [(r, "brainstorm") for r in failed_brainstorm]
        + [(r, "conversation") for r in failed_convo]
    )
    all_failed_sorted = sorted(
        all_failed,
        key=lambda x: parse_mongo_date(x[0].get("timestamp", "")),
        reverse=True,
    )
    worst_speaking_items = [
        _build_speaking_item(r, lms_type)
        for r, lms_type in all_failed_sorted[: config.WORST_SPEAKING_LIMIT]
    ]

    return {
        "participated": True,
        "session_count": len(sessions),
        "session_metrics": compute_session_metrics(sessions, results),
        "is_completed": len(completed_sessions) > 0,
        "completion_pct": max_completion,
        "latest_session_date": latest_date,
        "pronunciation_attempts": len(pron_items),
        "pronunciation_score_avg": pronunciation_score_avg,
        "free_speaking_attempts": len(free_items),
        "free_speaking_score_avg": free_speaking_score_avg,
        "free_speaking_answer_type_dist": dict(answer_type_dist),
        "brainstorm_attempts": len(brainstorm_items),
        "brainstorm_score_avg": brainstorm_score_avg,
        "brainstorm_answer_type_dist": dict(brainstorm_answer_type_dist),
        "conversation_attempts": len(convo_items),
        "conversation_score_avg": conversation_score_avg,
        "worst_speaking_items": worst_speaking_items,
    }


def derive_status(in_class, homework):
    has_dt = in_class.get("participated", False)
    has_hw = homework.get("attempted", False)
    if has_dt and has_hw:
        return "completed"
    if has_dt and not has_hw:
        return "in_class_only"
    if not has_dt and has_hw:
        return "homework_only"
    return "not_started"


def compute_weakness_score(homework, in_class) -> float:
    components = []

    bt = homework.get("bai_tap") or {}
    if bt.get("score") is not None:
        components.append((1.0 - bt["score"], 0.35))

    lt = homework.get("luyen_tap") or {}
    if lt.get("score") is not None:
        components.append((1.0 - lt["score"], 0.15))

    fs = in_class.get("free_speaking_score_avg")
    bs = in_class.get("brainstorm_score_avg")
    spoken = None
    if fs is not None and bs is not None:
        spoken = min(fs, bs)
    elif fs is not None:
        spoken = fs
    elif bs is not None:
        spoken = bs
    if spoken is not None:
        components.append((1.0 - spoken / 100.0, 0.50))
    elif in_class.get("participated"):
        pron = in_class.get("pronunciation_score_avg")
        if pron is not None:
            components.append((1.0 - pron / 100.0, 0.25))

    if not components:
        return 0.0

    total_weight = sum(w for _, w in components)
    weighted_sum = sum(score * w for score, w in components)
    return round(weighted_sum / total_weight, 4)


def latest_activity_date(*dates):
    valid = [d for d in dates if d]
    return max(valid) if valid else None
