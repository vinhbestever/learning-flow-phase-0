from __future__ import annotations

import statistics


def evaluate_signal_adherence(homework_list: list[dict], student_context: dict) -> dict:
    candidates = student_context["scored_candidates"]
    cand_map = {c["lesson_id"]: c for c in candidates}
    summary = student_context["summary"]

    selected_ids = {q["lesson_id"] for q in homework_list}

    sel_scores = [cand_map[lid]["composite_priority_score"] for lid in selected_ids if lid in cand_map]
    avg_priority = statistics.mean(sel_scores) if sel_scores else 0.0

    critical_ids = {c["lesson_id"] for c in candidates if c["weakness_score"] > 0.5}
    critical_covered = len(critical_ids & selected_ids) / max(len(critical_ids), 1)

    top3 = sorted(candidates, key=lambda c: -c["composite_priority_score"])[:3]
    top3_ids = {c["lesson_id"] for c in top3}
    top3_covered = len(top3_ids & selected_ids)

    not_attempted_ids = {c["lesson_id"] for c in candidates if c["homework_status"] == "not_attempted"}
    na_covered = len(not_attempted_ids & selected_ids) / max(len(not_attempted_ids), 1)

    _raw_fs = summary.get("overall_free_speaking_score_avg")
    free_speaking_avg = 100 if _raw_fs is None else _raw_fs
    needed_speaking = 5 if free_speaking_avg < 30 else 4 if free_speaking_avg < 50 else 3
    speaking_count = sum(1 for q in homework_list if q["skill_category"] == "speaking")
    free_speaking_ok = speaking_count >= needed_speaking

    oldest5 = sorted(candidates, key=lambda c: -c["days_since_last_practice"])[:5]
    oldest5_ids = {c["lesson_id"] for c in oldest5}
    oldest_covered = len(oldest5_ids & selected_ids)

    tier_dist: dict[str, int] = {"critical": 0, "spaced_rep": 0, "maintenance": 0, "unknown": 0}
    for q in homework_list:
        lid = q["lesson_id"]
        if lid not in cand_map:
            tier_dist["unknown"] += 1
        elif cand_map[lid]["weakness_score"] > 0.5:
            tier_dist["critical"] += 1
        elif cand_map[lid]["days_since_last_practice"] > 14:
            tier_dist["spaced_rep"] += 1
        else:
            tier_dist["maintenance"] += 1

    score = (
        0.30 * min(avg_priority, 1.0)
        + 0.25 * critical_covered
        + 0.20 * (top3_covered / 3)
        + 0.15 * na_covered
        + 0.10 * (oldest_covered / 5)
    )

    return {
        "score": round(score, 4),
        "avg_priority_score_selected": round(avg_priority, 4),
        "critical_tier_coverage": round(critical_covered, 4),
        "top3_urgent_covered": top3_covered,
        "not_attempted_coverage": round(na_covered, 4),
        "speaking_count": speaking_count,
        "free_speaking_needed_speaking": needed_speaking,
        "free_speaking_emphasis_ok": free_speaking_ok,
        "oldest5_covered": oldest_covered,
        "tier_distribution": tier_dist,
    }
