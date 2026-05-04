#!/usr/bin/env python3
"""
evaluate.py — Evaluate homework pipeline quality across 4 dimensions:
  1. Preprocess quality  — student_context.json signal analysis
  2. Constraint compliance — selector rule adherence per model
  3. Signal adherence — did model prioritize the right lessons?
  4. Reason field quality — LLM-as-judge (OpenAI)

Usage:
  python3 evaluate.py 2102555                           # full eval
  python3 evaluate.py 2102555 --skip-llm               # automated only (no API cost)
  python3 evaluate.py 2102555 --judge-model gpt-4.1    # specify judge model
  python3 evaluate.py 2102555 --models gpt-5.4,gpt-4.1 # evaluate subset
"""

from __future__ import annotations

import argparse
import json
import os
import re
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(student_id: str) -> tuple[dict, dict, dict | None]:
    base = Path("output") / student_id
    with open(base / "student_context.json", encoding="utf-8") as f:
        student_context = json.load(f)
    with open(base / "homework_by_model.json", encoding="utf-8") as f:
        homework_by_model = json.load(f)
    qe_path = base / "questions_export.json"
    questions_export = None
    if qe_path.exists():
        with open(qe_path, encoding="utf-8") as f:
            questions_export = json.load(f)
    return student_context, homework_by_model, questions_export


def build_question_id_set(questions_export: dict | None) -> set[int]:
    qids: set[int] = set()
    if not questions_export:
        return qids
    for lesson in questions_export.get("lessons", []):
        for section in ("bai_tap", "luyen_tap"):
            hw_sec = lesson.get("homework", {}).get(section, {})
            for q in hw_sec.get("questions", []):
                qid = q.get("question_id")
                if qid is not None:
                    qids.add(qid)
    return qids


# ---------------------------------------------------------------------------
# Part 1: Preprocess quality
# ---------------------------------------------------------------------------

def evaluate_preprocess(student_context: dict) -> dict:
    summary = student_context["summary"]
    candidates = student_context["scored_candidates"]

    scores = [c["composite_priority_score"] for c in candidates]
    forgetting_scores = [c["forgetting_score"] for c in candidates]
    weakness_scores = [c["weakness_score"] for c in candidates]
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

    # Signal coverage
    n_failed_text = sum(1 for c in candidates if c.get("failed_text_questions"))
    n_speaking = sum(1 for c in candidates if c.get("worst_speaking_items"))
    n_preview = sum(1 for c in candidates if c.get("question_bank_preview"))
    n_media = sum(1 for c in candidates if c.get("failed_media_questions_count", 0) > 0)
    no_signal = [
        c for c in candidates
        if not c.get("failed_text_questions")
        and not c.get("worst_speaking_items")
        and not c.get("failed_media_questions_count")
        and not c.get("question_bank_preview")
    ]

    stability_days = summary.get("stability_days", 1)
    # Forgetting ceiling: with low stability, all old lessons converge to ≈1.0
    forgetting_at_1 = sum(1 for s in forgetting_scores if s >= 0.999)

    # Tier breakdown
    n_critical = sum(1 for c in candidates if c["weakness_score"] > 0.5)
    n_spaced = sum(
        1 for c in candidates
        if c["days_since_last_practice"] > 14 and c["weakness_score"] <= 0.5
    )
    n_maintenance = n - n_critical - n_spaced

    # Speaking summary
    brainstorm_avg = summary.get("overall_brainstorm_score_avg", 100)
    free_speaking_avg = summary.get("overall_free_speaking_score_avg")
    pronunciation_avg = summary.get("overall_pronunciation_score_avg")
    conversation_avg = summary.get("overall_conversation_score_avg")
    weak_skills = summary.get("weak_skills_global", [])

    # Identify issues
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
            f"FORGETTING CEILING: {forgetting_at_1}/{n} candidates ({forgetting_at_1/n:.0%}) "
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


# ---------------------------------------------------------------------------
# Part 2: Constraint compliance
# ---------------------------------------------------------------------------

_VN_RE = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ"
    r"ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]"
)


def evaluate_constraints(homework_list: list[dict], cand_map: dict) -> dict:
    checks: dict[str, bool] = {}

    # 1. Exactly 15 questions
    checks["count_15"] = len(homework_list) == 15

    # 2. Skill distribution
    skill_counts = Counter(q["skill_category"] for q in homework_list)
    checks["speaking_ge3"] = skill_counts.get("speaking", 0) >= 3
    checks["grammar_ge4"] = skill_counts.get("grammar", 0) >= 4
    checks["vocab_ge3"] = skill_counts.get("vocabulary", 0) >= 3

    # 3. Per-lesson caps
    lesson_qs: dict[int, list[dict]] = defaultdict(list)
    for q in homework_list:
        lesson_qs[q["lesson_id"]].append(q)

    per_lesson_max = max((len(v) for v in lesson_qs.values()), default=0)
    checks["per_lesson_le2"] = per_lesson_max <= 2

    paired_violations: list[int] = []
    for lid, qs in lesson_qs.items():
        if len(qs) >= 2:
            skills = [q["skill_category"] for q in qs]
            if len(set(skills)) < len(skills):
                paired_violations.append(lid)
    checks["different_skills_when_paired"] = len(paired_violations) == 0

    # 4. Media ratio (0–4 acceptable; >4 would be too heavy)
    media_count = sum(1 for q in homework_list if q.get("requires_media"))
    checks["media_count_le4"] = media_count <= 4

    # 5. Reasons in Vietnamese
    n_vn = sum(1 for q in homework_list if _VN_RE.search(q.get("reason", "")))
    checks["all_reasons_vietnamese"] = n_vn == len(homework_list)

    # 6. All lesson_ids exist in scored_candidates
    invalid_lesson_ids = [q["lesson_id"] for q in homework_list if q["lesson_id"] not in cand_map]
    checks["valid_lesson_ids"] = len(invalid_lesson_ids) == 0

    score = sum(1 for v in checks.values() if v) / max(len(checks), 1)

    return {
        "score": round(score, 4),
        "passed": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "checks": checks,
        "skill_distribution": dict(skill_counts),
        "per_lesson_max": per_lesson_max,
        "media_count": media_count,
        "reasons_vn_count": n_vn,
        "paired_skill_violations": paired_violations,
        "invalid_lesson_ids": invalid_lesson_ids,
    }


# ---------------------------------------------------------------------------
# Part 3: Signal adherence
# ---------------------------------------------------------------------------

def evaluate_signal_adherence(homework_list: list[dict], student_context: dict) -> dict:
    candidates = student_context["scored_candidates"]
    cand_map = {c["lesson_id"]: c for c in candidates}
    summary = student_context["summary"]

    selected_ids = {q["lesson_id"] for q in homework_list}

    # Avg composite priority score of selected lessons
    sel_scores = [cand_map[lid]["composite_priority_score"] for lid in selected_ids if lid in cand_map]
    avg_priority = statistics.mean(sel_scores) if sel_scores else 0.0

    # Critical tier coverage
    critical_ids = {c["lesson_id"] for c in candidates if c["weakness_score"] > 0.5}
    critical_covered = len(critical_ids & selected_ids) / max(len(critical_ids), 1)

    # Top-3 most urgent lessons covered
    top3 = sorted(candidates, key=lambda c: -c["composite_priority_score"])[:3]
    top3_ids = {c["lesson_id"] for c in top3}
    top3_covered = len(top3_ids & selected_ids)

    # Not-attempted homework coverage
    not_attempted_ids = {c["lesson_id"] for c in candidates if c["homework_status"] == "not_attempted"}
    na_covered = len(not_attempted_ids & selected_ids) / max(len(not_attempted_ids), 1)

    # Brainstorm emphasis: if brainstorm avg < 30 → need ≥5 speaking; < 50 → ≥4; else ≥3
    brainstorm_avg = summary.get("overall_brainstorm_score_avg", 100)
    needed_speaking = 5 if brainstorm_avg < 30 else 4 if brainstorm_avg < 50 else 3
    speaking_count = sum(1 for q in homework_list if q["skill_category"] == "speaking")
    brainstorm_ok = speaking_count >= needed_speaking

    # Oldest 5 lessons covered
    oldest5 = sorted(candidates, key=lambda c: -c["days_since_last_practice"])[:5]
    oldest5_ids = {c["lesson_id"] for c in oldest5}
    oldest_covered = len(oldest5_ids & selected_ids)

    # Tier distribution across selected questions
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

    # Weighted signal score
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
        "brainstorm_needed_speaking": needed_speaking,
        "brainstorm_emphasis_ok": brainstorm_ok,
        "oldest5_covered": oldest_covered,
        "tier_distribution": tier_dist,
    }


# ---------------------------------------------------------------------------
# Part 4: LLM-as-Judge
# ---------------------------------------------------------------------------

def _lesson_context_for_judge(lesson_id: int, student_context: dict) -> str:
    cand_map = {c["lesson_id"]: c for c in student_context["scored_candidates"]}
    c = cand_map.get(lesson_id)
    if not c:
        return "No candidate data available."

    lines = [
        f"Lesson: {c.get('title', 'Unknown')} | "
        f"{c.get('days_since_last_practice', '?')} days since last practice | "
        f"weakness={c.get('weakness_score', '?'):.2f} | "
        f"hw_status={c.get('homework_status', '?')}"
    ]
    for fq in (c.get("failed_text_questions") or [])[:3]:
        lines.append(
            f"  [FAILED] Q: {fq.get('question_text','')[:80]} | "
            f"correct={fq.get('correct_answer')} | student={fq.get('student_answer')}"
        )
    for si in (c.get("worst_speaking_items") or [])[:3]:
        lines.append(
            f"  [SPEAKING/{si.get('lms_type')}] Q: {si.get('question','')[:60]} | "
            f"said='{si.get('user_transcript','')}' | score={si.get('score')} | type={si.get('answer_type')}"
        )
    for pq in (c.get("question_bank_preview") or [])[:2]:
        lines.append(f"  [PREVIEW] {pq.get('question_text','')[:80]}")
    return "\n".join(lines)


_REASON_RUBRIC_PROMPT = """\
You are evaluating the "reason" field written by an AI homework-assignment system \
for a Vietnamese English learner (elementary level, ~10 years old).

STUDENT CONTEXT:
- Brainstorm (image→name visual targets) avg: {brainstorm_avg}/100 — CRITICAL weakness
- Free speaking avg: {free_speaking_avg}/100
- Pronunciation avg: {pronunciation_avg}/100
- Written homework accuracy: ~94% (strong)

HOMEWORK QUESTION BEING ASSIGNED:
- lesson: {lesson_title}
- skill_category: {skill_category}
- question_type: {question_type}
- question_text: {question_text}
- correct_answer: {correct_answer}

ACTUAL STUDENT DATA FOR THIS LESSON:
{lesson_context}

REASON FIELD TO EVALUATE:
"{reason}"

Rate on each dimension (1=poor, 5=excellent):
- specificity: Cites a specific wrong answer, transcript, or concrete error (not generic)
- timing: Mentions when the lesson was last practiced (days/weeks/months)
- data_accuracy: Consistent with the actual student data above (no invented facts)
- actionability: Helps teacher/student understand exactly what to work on and why
- language_quality: Natural Vietnamese (fluent, not machine-translated feel)

Return ONLY JSON: {{"specificity": N, "timing": N, "data_accuracy": N, "actionability": N, "language_quality": N, "comment": "one-sentence note in English"}}"""

_DIAGNOSTIC_RUBRIC_PROMPT = """\
You are evaluating a diagnostic analysis written by an AI model about a Vietnamese \
English learner's weaknesses. This diagnostic is used to brief a homework-selector agent.

ACTUAL STUDENT DATA:
- Brainstorm (image→name targets) avg: {brainstorm_avg}/100 — this is the CRITICAL weakness
- Free speaking avg: {free_speaking_avg}/100
- Pronunciation avg: {pronunciation_avg}/100
- Written homework accuracy: {homework_accuracy} (strong — do NOT flag this as a weakness)
- Total lessons: {total_lessons}, completed: {completed}
- Forgetting: most lessons were studied 7–120 days ago

DIAGNOSTIC TEXT (first 1200 chars):
{diagnostic}

Rate on each dimension (1=poor, 5=excellent):
- weakness_identification: Correctly identifies brainstorm/speaking as primary weakness \
(not written accuracy which is already strong)
- pattern_depth: Explains WHY failures happen, not just lists them
- actionability: Gives clear guidance the selector agent can act on
- specificity: Cites specific lesson titles, scores, or student transcripts

Return ONLY JSON: {{"weakness_identification": N, "pattern_depth": N, "actionability": N, "specificity": N, "comment": "one-sentence note in English"}}"""


def _openai_json(client, model: str, prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def evaluate_reasons_llm(
    homework_by_model: dict,
    student_context: dict,
    judge_model: str,
    models_to_eval: list[str],
    sample_n: int = 5,
) -> dict:
    import openai
    client = openai.OpenAI()
    summary = student_context["summary"]

    brainstorm_avg = summary.get("overall_brainstorm_score_avg", "?")
    free_speaking_avg = summary.get("overall_free_speaking_score_avg", "?")
    pronunciation_avg = summary.get("overall_pronunciation_score_avg", "?")
    homework_accuracy = next(
        iter(summary.get("overall_homework_skill_breakdown", {}).values()), {}
    ).get("accuracy", "?")
    total_lessons = summary.get("total_lessons", "?")
    completed = summary.get("lessons_by_status", {}).get("completed", "?")

    results: dict[str, dict] = {}

    for model_name in models_to_eval:
        model_data = homework_by_model["models"].get(model_name, {})
        hw = model_data.get("homework", [])
        diagnostic = model_data.get("diagnostic", "")

        print(f"  [{model_name}] judging reasons... ", end="", flush=True)

        # Sample questions
        sample = random.sample(hw, min(sample_n, len(hw)))
        reason_scores: list[dict] = []
        for q in sample:
            lesson_ctx = _lesson_context_for_judge(q["lesson_id"], student_context)
            prompt = _REASON_RUBRIC_PROMPT.format(
                brainstorm_avg=brainstorm_avg,
                free_speaking_avg=free_speaking_avg,
                pronunciation_avg=pronunciation_avg,
                lesson_title=q.get("lesson_title", ""),
                skill_category=q.get("skill_category", ""),
                question_type=q.get("question_type", ""),
                question_text=(q.get("question_text") or "")[:150],
                correct_answer=q.get("correct_answer", ""),
                lesson_context=lesson_ctx,
                reason=q.get("reason", ""),
            )
            try:
                scores = _openai_json(client, judge_model, prompt)
                scores["question_no"] = q.get("question_no")
                scores["reason_preview"] = (q.get("reason") or "")[:80]
            except Exception as exc:
                scores = {"question_no": q.get("question_no"), "error": str(exc)}
            reason_scores.append(scores)

        # Aggregate reason scores
        dims = ["specificity", "timing", "data_accuracy", "actionability", "language_quality"]
        valid = [s for s in reason_scores if "error" not in s]
        agg: dict[str, float | None] = {}
        if valid:
            for dim in dims:
                vals = [s[dim] for s in valid if isinstance(s.get(dim), (int, float))]
                agg[dim] = round(statistics.mean(vals), 2) if vals else None
            dim_vals = [v for v in agg.values() if v is not None]
            agg["overall"] = round(statistics.mean(dim_vals), 2) if dim_vals else None

        print(f"avg={agg.get('overall', 'N/A')} | judging diagnostic... ", end="", flush=True)

        # Judge diagnostic
        diag_score: dict = {}
        try:
            diag_prompt = _DIAGNOSTIC_RUBRIC_PROMPT.format(
                brainstorm_avg=brainstorm_avg,
                free_speaking_avg=free_speaking_avg,
                pronunciation_avg=pronunciation_avg,
                homework_accuracy=homework_accuracy,
                total_lessons=total_lessons,
                completed=completed,
                diagnostic=diagnostic[:1200],
            )
            diag_score = _openai_json(client, judge_model, diag_prompt)
        except Exception as exc:
            diag_score = {"error": str(exc)}

        diag_dims = ["weakness_identification", "pattern_depth", "actionability", "specificity"]
        diag_vals = [diag_score.get(d) for d in diag_dims if isinstance(diag_score.get(d), (int, float))]
        diag_avg = round(statistics.mean(diag_vals), 2) if diag_vals else None
        print(f"diag={diag_avg}")

        results[model_name] = {
            "reason_scores_per_question": reason_scores,
            "reason_aggregated": agg,
            "diagnostic_score": diag_score,
            "diagnostic_avg": diag_avg,
        }

    return results


# ---------------------------------------------------------------------------
# Overall scoring & ranking
# ---------------------------------------------------------------------------

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
            # All 4 dimensions available
            overall = 0.25 * c_score + 0.35 * s_score + 0.25 * (r_overall / 5) + 0.15 * (d_avg / 5)
        elif r_overall is not None:
            overall = 0.25 * c_score + 0.35 * s_score + 0.40 * (r_overall / 5)
        else:
            # Automated only
            overall = 0.40 * c_score + 0.60 * s_score

        tier = "A" if overall >= 0.80 else "B" if overall >= 0.65 else "C"

        ranking.append({
            "model": model,
            "overall_score": round(overall * 100, 1),
            "tier": tier,
            "constraint_score": round(c_score * 100, 1),
            "signal_score": round(s_score * 100, 1),
            "reason_score": round(r_overall, 2) if r_overall is not None else None,
            "diagnostic_score": round(d_avg, 2) if d_avg is not None else None,
        })

    ranking.sort(key=lambda x: -x["overall_score"])
    return ranking


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

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

    failing_paired = [m for m, cr in constraint_results.items() if not cr["checks"].get("different_skills_when_paired")]
    if failing_paired:
        suggestions.append(
            f"**[Selector]** Models with duplicate skill from same lesson: {failing_paired}. "
            "Reinforce the rule in the system prompt with an explicit example."
        )

    # Check if all models exclusively use critical-tier lessons (no spaced_rep/maintenance)
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
        suggestions.append(
            "No critical issues detected. Pipeline is operating within defined constraints."
        )

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

    # Model ranking
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

    # Constraint detail
    c_cols = [
        "count_15", "speaking_ge3", "grammar_ge4", "vocab_ge3",
        "per_lesson_le2", "different_skills_when_paired",
        "media_count_le4", "all_reasons_vietnamese", "valid_lesson_ids",
    ]
    c_headers = [
        "15q", "spk≥3", "grm≥4", "voc≥3",
        "≤2/less", "diff_skill", "media≤4", "VN reason", "valid IDs",
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

    # Signal detail
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

    # LLM judge
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

    # Improvements
    lines += ["---", "", f"## {section_idx}. Improvement Suggestions", ""]
    for s in _improvement_suggestions(prep, constraint_results, signal_results):
        lines.append(f"- {s}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate homework pipeline quality")
    parser.add_argument("student_id", help="Student ID (e.g. 2102555)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM-as-judge (no API calls)")
    parser.add_argument("--judge-model", default="gpt-4.1", help="OpenAI model to use as judge")
    parser.add_argument("--models", default=None, help="Comma-separated models to evaluate (default: all)")
    args = parser.parse_args()

    print(f"\nLoading data for student {args.student_id}...")
    student_context, homework_by_model, questions_export = load_data(args.student_id)

    cand_map = {c["lesson_id"]: c for c in student_context["scored_candidates"]}

    all_models = list(homework_by_model["models"].keys())
    models_to_eval = [m.strip() for m in args.models.split(",")] if args.models else all_models
    print(f"Models: {models_to_eval}")

    # 1. Preprocess
    print("\n[1/4] Preprocess quality...")
    prep = evaluate_preprocess(student_context)
    print(f"  Candidates: {prep['tier_breakdown']['total']} | Issues: {prep['issue_count']}")

    # 2. Constraints
    print("\n[2/4] Constraint compliance...")
    constraint_results: dict[str, dict] = {}
    for model in models_to_eval:
        hw = homework_by_model["models"][model].get("homework", [])
        constraint_results[model] = evaluate_constraints(hw, cand_map)
        cr = constraint_results[model]
        print(f"  {model:<30} {cr['score']:.2f} ({cr['passed']}/{cr['total']}) — {cr['skill_distribution']}")

    # 3. Signal adherence
    print("\n[3/4] Signal adherence...")
    signal_results: dict[str, dict] = {}
    for model in models_to_eval:
        hw = homework_by_model["models"][model].get("homework", [])
        signal_results[model] = evaluate_signal_adherence(hw, student_context)
        sr = signal_results[model]
        print(
            f"  {model:<30} score={sr['score']:.3f} "
            f"| priority={sr['avg_priority_score_selected']:.3f} "
            f"| critical={sr['critical_tier_coverage']:.0%} "
            f"| speaking={sr['speaking_count']}{'✓' if sr['brainstorm_emphasis_ok'] else '✗'}"
        )

    # 4. LLM judge
    llm_results: dict | None = None
    if not args.skip_llm:
        if os.environ.get("OPENAI_API_KEY"):
            print(f"\n[4/4] LLM-as-Judge with {args.judge_model}...")
            try:
                random.seed(42)
                llm_results = evaluate_reasons_llm(
                    homework_by_model, student_context, args.judge_model, models_to_eval
                )
            except Exception as exc:
                print(f"  LLM judge failed: {exc}")
        else:
            print("\n[4/4] Skipping LLM judge — OPENAI_API_KEY not set")
    else:
        print("\n[4/4] Skipping LLM judge (--skip-llm)")

    # Ranking
    ranking = compute_ranking(constraint_results, signal_results, llm_results)

    # Write reports
    output_dir = Path("output") / args.student_id
    json_path, md_path = write_report(
        args.student_id, prep, constraint_results, signal_results, llm_results, ranking, output_dir
    )

    print(f"\nReports saved:")
    print(f"  {json_path}")
    print(f"  {md_path}")

    # Console summary
    print("\n=== Model Ranking ===")
    hdr = f"{'Model':<30} {'Overall':>8} {'Tier':>4} {'Constraint':>11} {'Signal':>7}"
    if llm_results:
        hdr += f" {'Reason':>7} {'Diag':>5}"
    print(hdr)
    print("—" * len(hdr))
    for r in ranking:
        row = (
            f"{r['model']:<30} {r['overall_score']:>8.1f} {r['tier']:>4} "
            f"{r['constraint_score']:>11.1f} {r['signal_score']:>7.1f}"
        )
        if llm_results:
            row += f" {_fmt(r['reason_score']):>7} {_fmt(r['diagnostic_score']):>5}"
        print(row)

    if prep["issues"]:
        print(f"\n=== Preprocess Issues ({prep['issue_count']}) ===")
        for issue in prep["issues"]:
            print(f"  • {issue[:120]}")


if __name__ == "__main__":
    main()
