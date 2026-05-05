from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _fmt(v: float | None, suffix: str = "") -> str:
    return f"{v}{suffix}" if v is not None else "—"


def _improvement_suggestions(
    prep: dict,
    constraint_results: dict,
    signal_results: dict,
) -> list[str]:
    suggestions = []

    sp = prep["speaking_summary"]
    if sp["weak_skills_global_empty"] and sp["brainstorm_avg"] < 50 and not sp.get("critical_speaking_types"):
        suggestions.append(
            "**[Preprocess]** Add a `critical_speaking_types` field to `summary` "
            "exposing brainstorm/free_speaking weakness. Currently `weak_skills_global` only "
            "reflects LMS written accuracy, masking the speaking crisis."
        )

    stab = prep["forgetting_curve"]["stability_days"]
    ceil_threshold = 0.90 if stab >= 7 else 0.70
    if prep["forgetting_curve"]["at_ceiling_pct"] > ceil_threshold:
        suggestions.append(
            f"**[Preprocess]** Forgetting stability={stab:.0f}d ceiling: "
            f"{prep['forgetting_curve']['at_ceiling_count']}/{prep['tier_breakdown']['total']} "
            "candidates score ≈1.0. All lessons were last practiced >30 days ago — "
            "this reflects real student inactivity rather than a formula defect."
        )

    if prep["signal_coverage"]["no_signal_count"] > 0:
        suggestions.append(
            f"**[Preprocess]** {prep['signal_coverage']['no_signal_count']} candidate(s) "
            "passed the quality gate with zero actionable signals. Tighten the admission "
            "criterion or log a warning."
        )

    failing_speaking = [m for m, cr in constraint_results.items() if not cr["checks"].get("speaking_ge3")]
    if failing_speaking:
        suggestions.append(
            f"**[Selector]** Models breaking ≥3 speaking rule: {failing_speaking}. "
            "Consider dynamic threshold: `min_speaking = 5 if brainstorm<30 else 4 if brainstorm<50 else 3`."
        )

    failing_grammar = [m for m, cr in constraint_results.items() if not cr["checks"].get("grammar_ge4")]
    if failing_grammar:
        suggestions.append(
            f"**[Selector]** Models breaking ≥4 grammar rule: {failing_grammar}. "
            "Add a post-generation validation step that rejects and retries if hard constraints fail."
        )

    failing_paired = [
        m for m, cr in constraint_results.items() if not cr["checks"].get("different_skills_when_paired")
    ]
    if failing_paired:
        suggestions.append(
            f"**[Selector]** Models with duplicate skill from same lesson: {failing_paired}. "
            "Reinforce the rule in the system prompt with an explicit example."
        )

    all_critical_only = all(
        sr.get("tier_distribution", {}).get("spaced_rep", 0) == 0
        and sr.get("tier_distribution", {}).get("maintenance", 0) == 0
        for sr in signal_results.values()
    )
    if all_critical_only:
        suggestions.append(
            "**[Context Builder / Selector]** ALL models select exclusively from critical-tier lessons "
            "(spaced_rep=0, maintenance=0 in every output). Spaced-repetition candidates are present "
            "but never selected. Consider enforcing a tier-diversity requirement: "
            "at least 2 questions from spaced_rep tier when available."
        )

    if not suggestions:
        suggestions.append("No critical issues detected. Pipeline is operating within defined constraints.")

    return suggestions


def format_markdown(
    student_id: str,
    prep: dict,
    constraint_results: dict,
    signal_results: dict,
    llm_results: dict | None,
    ranking: list[dict],
    evaluated_at: str,
) -> str:
    lines: list[str] = [
        f"# Pipeline Quality Evaluation — Student {student_id}",
        f"_Evaluated: {evaluated_at[:19]} UTC_",
        "",
        "---",
        "",
        "## 1. Preprocess Quality",
        "",
        f"**Candidates:** {prep['tier_breakdown']['total']} total "
        f"| Critical: {prep['tier_breakdown']['critical']} "
        f"| Spaced-rep: {prep['tier_breakdown']['spaced_rep']} "
        f"| Maintenance: {prep['tier_breakdown']['maintenance']}",
        "",
        "**Score distribution (composite_priority_score):**",
        (
            f"mean={prep['score_distribution']['mean']} "
            f"± {prep['score_distribution']['std']} "
            f"| range [{prep['score_distribution']['min']}, {prep['score_distribution']['max']}] "
            f"| p25/median/p75 = {prep['score_distribution']['p25']} / "
            f"{prep['score_distribution']['median']} / {prep['score_distribution']['p75']}"
        ),
        "",
        "**Signal coverage across candidates:**",
        f"- Failed text questions: {prep['signal_coverage']['with_failed_text']:.0%}",
        f"- Speaking failures: {prep['signal_coverage']['with_speaking_items']:.0%}",
        f"- Question bank preview: {prep['signal_coverage']['with_question_preview']:.0%}",
        f"- No-signal candidates: {prep['signal_coverage']['no_signal_count']}",
        "",
        "**Speaking averages:**",
        f"- Brainstorm: **{prep['speaking_summary']['brainstorm_avg']}/100**"
        + (" ⚠️ CRITICAL" if (prep["speaking_summary"]["brainstorm_avg"] or 100) < 50 else ""),
        f"- Free speaking: {prep['speaking_summary']['free_speaking_avg']}/100",
        f"- Pronunciation: {prep['speaking_summary']['pronunciation_avg']}/100",
        f"- Conversation: {prep['speaking_summary']['conversation_avg']}/100",
        f"- `weak_skills_global` empty: **{prep['speaking_summary']['weak_skills_global_empty']}** "
        + ("← speaking crisis not visible here" if prep["speaking_summary"]["weak_skills_global_empty"] else ""),
        "",
        f"**Forgetting ceiling:** {prep['forgetting_curve']['at_ceiling_count']} / "
        f"{prep['tier_breakdown']['total']} candidates ({prep['forgetting_curve']['at_ceiling_pct']:.0%}) "
        f"at forgetting_score≈1.0 (stability={prep['forgetting_curve']['stability_days']:.0f}d)",
        "",
    ]

    if prep["issues"]:
        lines += ["**Issues found:**", ""]
        for i, issue in enumerate(prep["issues"], 1):
            lines.append(f"{i}. {issue}")
        lines.append("")
    else:
        lines += ["_No issues found._", ""]

    lines += [
        "---",
        "",
        "## 2. Model Ranking",
        "",
        "Scoring weights: Constraint 25% | Signal 35% | Reason quality 25% | Diagnostic 15%",
        "_(When LLM judge unavailable: Constraint 40% | Signal 60%)_",
        "",
        "| Model | Overall | Tier | Constraint | Signal | Reason/5 | Diagnostic/5 |",
        "|-------|---------|------|------------|--------|----------|--------------|",
    ]
    for r in ranking:
        lines.append(
            f"| {r['model']} | **{r['overall_score']}** | {r['tier']} "
            f"| {r['constraint_score']} | {r['signal_score']} "
            f"| {_fmt(r['reason_score'])} | {_fmt(r['diagnostic_score'])} |"
        )
    lines.append("")

    c_cols = [
        "count_15",
        "speaking_ge3",
        "grammar_ge4",
        "vocab_ge3",
        "per_lesson_le2",
        "different_skills_when_paired",
        "media_count_le4",
        "all_reasons_vietnamese",
        "valid_lesson_ids",
    ]
    c_headers = [
        "15q",
        "spk≥3",
        "grm≥4",
        "voc≥3",
        "≤2/less",
        "diff_skill",
        "media≤4",
        "VN reason",
        "valid IDs",
    ]
    lines += [
        "---",
        "",
        "## 3. Constraint Compliance",
        "",
        "| Model | Score | " + " | ".join(c_headers) + " |",
        "|" + "-------|" * (len(c_cols) + 2),
    ]
    for model, cr in sorted(constraint_results.items()):
        cells = ["✓" if cr["checks"].get(col) else "✗" for col in c_cols]
        lines.append(
            f"| {model} | {cr['score']:.2f} ({cr['passed']}/{cr['total']}) | "
            + " | ".join(cells)
            + " |"
        )
    lines.append("")

    lines += [
        "---",
        "",
        "## 4. Signal Adherence",
        "",
        "| Model | Score | Avg Priority | Critical% | Top3 | NA cov. | Speaking | Old5 | Tier dist (c/s/m) |",
        "|-------|-------|-------------|-----------|------|---------|----------|------|--------------------|",
    ]
    for model, sr in sorted(signal_results.items()):
        td = sr["tier_distribution"]
        lines.append(
            f"| {model} | {sr['score']:.3f} "
            f"| {sr['avg_priority_score_selected']:.3f} "
            f"| {sr['critical_tier_coverage']:.0%} "
            f"| {sr['top3_urgent_covered']}/3 "
            f"| {sr['not_attempted_coverage']:.0%} "
            f"| {sr['speaking_count']}{'✓' if sr['brainstorm_emphasis_ok'] else '✗'}(≥{sr['brainstorm_needed_speaking']}) "
            f"| {sr['oldest5_covered']}/5 "
            f"| {td['critical']}/{td['spaced_rep']}/{td['maintenance']} |"
        )
    lines.append("")

    section_idx = 5
    if llm_results:
        lines += [
            "---",
            "",
            f"## {section_idx}. LLM-as-Judge (Reason & Diagnostic Quality)",
            "",
            "| Model | Reason avg | Specificity | Timing | Accuracy | Actionability | Language | Diagnostic |",
            "|-------|-----------|------------|--------|----------|--------------|----------|------------|",
        ]
        for model, lr in sorted(llm_results.items()):
            agg = lr.get("reason_aggregated", {})
            d_avg = lr.get("diagnostic_avg")

            def f(k: str) -> str:
                return _fmt(agg.get(k))

            lines.append(
                f"| {model} | {_fmt(agg.get('overall'))} "
                f"| {f('specificity')} | {f('timing')} | {f('data_accuracy')} "
                f"| {f('actionability')} | {f('language_quality')} "
                f"| {_fmt(d_avg)} |"
            )
        lines.append("")
        section_idx += 1

    lines += ["---", "", f"## {section_idx}. Improvement Suggestions", ""]
    for s in _improvement_suggestions(prep, constraint_results, signal_results):
        lines.append(f"- {s}")
    lines.append("")

    return "\n".join(lines)


def write_report(
    student_id: str,
    prep: dict,
    constraint_results: dict,
    signal_results: dict,
    llm_results: dict | None,
    ranking: list[dict],
    output_dir: Path,
) -> tuple[Path, Path]:
    now = datetime.now(timezone.utc).isoformat()

    full = {
        "student_id": student_id,
        "evaluated_at": now,
        "preprocess": prep,
        "model_ranking": [r["model"] for r in ranking],
        "models": {},
    }
    all_models = sorted(set(constraint_results) | set(signal_results))
    for model in all_models:
        full["models"][model] = {
            "constraint": constraint_results.get(model),
            "signal": signal_results.get(model),
            "llm_judge": (llm_results or {}).get(model),
            "summary": next((r for r in ranking if r["model"] == model), {}),
        }

    json_path = output_dir / "evaluation_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)

    md = format_markdown(student_id, prep, constraint_results, signal_results, llm_results, ranking, now)
    md_path = output_dir / "evaluation_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    return json_path, md_path
