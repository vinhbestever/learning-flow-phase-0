from __future__ import annotations

import statistics


def evaluate_preprocess(student_context: dict) -> dict:
    summary = student_context["summary"]
    candidates = student_context["scored_candidates"]

    scores = [c["composite_priority_score"] for c in candidates]
    forgetting_scores = [c["forgetting_score"] for c in candidates]
    n = len(scores)

    sorted_scores = sorted(scores)
    score_dist = {
        "count": n,
        "mean": round(statistics.mean(scores), 4),
        "std": round(statistics.stdev(scores) if n > 1 else 0, 4),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "p25": round(sorted_scores[n // 4], 4),
        "median": round(sorted_scores[n // 2], 4),
        "p75": round(sorted_scores[3 * n // 4], 4),
    }

    n_failed_text = sum(1 for c in candidates if c.get("failed_text_questions"))
    n_speaking = sum(1 for c in candidates if c.get("worst_speaking_items"))
    n_preview = sum(1 for c in candidates if c.get("question_bank_preview"))
    n_media = sum(1 for c in candidates if c.get("failed_media_questions_count", 0) > 0)
    no_signal = [
        c
        for c in candidates
        if not c.get("failed_text_questions")
        and not c.get("worst_speaking_items")
        and not c.get("failed_media_questions_count")
        and not c.get("question_bank_preview")
    ]

    stability_days = summary.get("stability_days", 1)
    forgetting_at_1 = sum(1 for s in forgetting_scores if s >= 0.999)

    n_critical = sum(1 for c in candidates if c["weakness_score"] > 0.5)
    n_spaced = sum(
        1 for c in candidates if c["days_since_last_practice"] > 14 and c["weakness_score"] <= 0.5
    )
    n_maintenance = n - n_critical - n_spaced

    brainstorm_avg = summary.get("overall_brainstorm_score_avg", 100)
    free_speaking_avg = summary.get("overall_free_speaking_score_avg")
    pronunciation_avg = summary.get("overall_pronunciation_score_avg")
    conversation_avg = summary.get("overall_conversation_score_avg")
    weak_skills = summary.get("weak_skills_global", [])

    issues: list[str] = []

    critical_speaking_types = summary.get("critical_speaking_types", [])
    if brainstorm_avg < 50 and not weak_skills and not critical_speaking_types:
        issues.append(
            f"DESIGN GAP: weak_skills_global=[] despite brainstorm_avg={brainstorm_avg}/100. "
            "Speaking weakness is invisible to any code that reads weak_skills_global — "
            "only LMS homework accuracy is captured there, not speaking scores."
        )

    ceiling_threshold = 0.90 if stability_days >= 7 else 0.70
    if forgetting_at_1 / n > ceiling_threshold:
        issues.append(
            f"FORGETTING CEILING: {forgetting_at_1}/{n} candidates ({forgetting_at_1 / n:.0%}) "
            f"have forgetting_score≈1.0 (stability={stability_days:.0f}d). "
            "All candidates were last studied >30 days ago — forgetting scores are uniformly high."
        )

    if no_signal:
        ids = [c["lesson_id"] for c in no_signal]
        issues.append(
            f"EMPTY SIGNAL: {len(no_signal)} candidate(s) passed the quality gate with "
            f"no failed questions, no speaking items, no media fails, no preview: {ids}"
        )

    if score_dist["std"] < 0.05:
        issues.append(
            f"LOW VARIANCE: score std={score_dist['std']}. "
            "Scoring formula may not discriminate well between lessons."
        )

    return {
        "score_distribution": score_dist,
        "tier_breakdown": {
            "critical": n_critical,
            "spaced_rep": n_spaced,
            "maintenance": n_maintenance,
            "total": n,
        },
        "signal_coverage": {
            "with_failed_text": round(n_failed_text / n, 3),
            "with_speaking_items": round(n_speaking / n, 3),
            "with_question_preview": round(n_preview / n, 3),
            "with_media_failures": round(n_media / n, 3),
            "no_signal_count": len(no_signal),
        },
        "forgetting_curve": {
            "at_ceiling_count": forgetting_at_1,
            "at_ceiling_pct": round(forgetting_at_1 / n, 3),
            "stability_days": stability_days,
            "note": f"All lessons have 1 prior attempt. Stability={stability_days:.0f}d.",
        },
        "speaking_summary": {
            "brainstorm_avg": brainstorm_avg,
            "free_speaking_avg": free_speaking_avg,
            "pronunciation_avg": pronunciation_avg,
            "conversation_avg": conversation_avg,
            "weak_skills_global_empty": not bool(weak_skills),
            "critical_speaking_types": summary.get("critical_speaking_types", []),
        },
        "issues": issues,
        "issue_count": len(issues),
    }
