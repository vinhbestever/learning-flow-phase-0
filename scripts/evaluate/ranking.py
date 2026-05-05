from __future__ import annotations


def compute_ranking(
    constraint_results: dict,
    signal_results: dict,
    llm_results: dict | None,
) -> list[dict]:
    all_models = sorted(set(constraint_results) | set(signal_results))
    ranking = []

    for model in all_models:
        c = constraint_results.get(model, {})
        s = signal_results.get(model, {})
        r = (llm_results or {}).get(model, {})

        c_score = c.get("score", 0.0)
        s_score = s.get("score", 0.0)

        r_overall = r.get("reason_aggregated", {}).get("overall") if r else None
        d_avg = r.get("diagnostic_avg") if r else None

        if r_overall is not None and d_avg is not None:
            overall = 0.25 * c_score + 0.35 * s_score + 0.25 * (r_overall / 5) + 0.15 * (d_avg / 5)
        elif r_overall is not None:
            overall = 0.25 * c_score + 0.35 * s_score + 0.40 * (r_overall / 5)
        else:
            overall = 0.40 * c_score + 0.60 * s_score

        tier = "A" if overall >= 0.80 else "B" if overall >= 0.65 else "C"

        ranking.append(
            {
                "model": model,
                "overall_score": round(overall * 100, 1),
                "tier": tier,
                "constraint_score": round(c_score * 100, 1),
                "signal_score": round(s_score * 100, 1),
                "reason_score": round(r_overall, 2) if r_overall is not None else None,
                "diagnostic_score": round(d_avg, 2) if d_avg is not None else None,
            }
        )

    ranking.sort(key=lambda x: -x["overall_score"])
    return ranking
