#!/usr/bin/env python3
"""
Aggregate diagnostic + homework quality metrics across students/models.
Outputs a single CSV for manual review (Vietnamese notes column).

Excludes gpt-5.4-pro by default (user comparison set).
Run from repo root: python scripts/analyze_pipeline_model_outputs.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUTPUT = REPO / "output"

STUDENTS = ["2102555", "2109886", "1585392_newstudent"]
EXCLUDE_MODELS = frozenset({"gpt-5.4-pro"})


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def count_quoted_fragments(text: str) -> int:
    """Rough proxy for citing student utterances / short examples."""
    if not text:
        return 0
    n = text.count('"') + text.count("\u201c") + text.count("\u201d")
    return n // 2


def count_example_markers(text: str) -> int:
    """Examples without ASCII quotes (Vietnamese diagnostics)."""
    if not text:
        return 0
    arrows = text.count("→")
    eg = len(re.findall(r"\bví dụ\b", text, re.I))
    return arrows + min(eg, 5)


def count_lesson_like_refs(text: str) -> int:
    """Unit/Lesson titles and homework_status style anchors."""
    if not text:
        return 0
    u = len(re.findall(r"Unit\s+\d", text, re.I))
    h = text.lower().count("hw_status")
    days = len(re.findall(r"\b\d{1,3}\s*ngày", text, re.I))
    return u + h + min(days, 5)


def diagnostic_actionability(text: str) -> float:
    """0–1: imperative / recommendation language density."""
    if not text:
        return 0.0
    markers = (
        "cần ", "nên ", "ưu tiên", "luyện", "tập trung", "củng cố",
        "tránh", "sửa", "nhớ", "ôn lại",
    )
    t = text.lower()
    hits = sum(1 for m in markers if m in t)
    return min(1.0, hits / 6.0)


def build_valid_sets(student_id: str) -> tuple[set[int], set[int], set[str], list[str]]:
    """tiered lesson ids, question ids in pool, candidate titles for title overlap."""
    from agents.context_builder import build_context

    out = OUTPUT / student_id
    ctx = load_json(out / "student_context.json")
    qexp = load_json(out / "questions_export.json")
    tiered, pool = build_context(ctx, qexp)
    lessons = {c["lesson_id"] for c in tiered}
    qids = set()
    for q in pool:
        qid = q.get("question_id")
        if qid is not None:
            qids.add(int(qid))
    titles = []
    for c in tiered:
        t = (c.get("title") or "").strip()
        if t:
            titles.append(t.lower())
    return lessons, qids, set(titles), titles


def title_overlap_score(diagnostic: str, titles_lower: list[str]) -> float:
    if not diagnostic or not titles_lower:
        return 0.0
    d = diagnostic.lower()
    hits = sum(1 for t in titles_lower if len(t) > 12 and t in d)
    return min(1.0, hits / max(3, len(titles_lower) * 0.25))


def homework_metrics(
    items: list,
    valid_lessons: set[int],
    valid_qids: set[int],
) -> dict:
    n = len(items)
    if n == 0:
        return {
            "n_questions": 0,
            "unique_lessons": 0,
            "unique_qids": 0,
            "skill_categories": "",
            "avg_reason_chars": 0.0,
            "median_reason_chars": 0.0,
            "pct_lesson_in_tier": 0.0,
            "pct_question_in_pool": 0.0,
            "difficulty_dist": "",
        }
    lids = []
    qids = []
    reasons = []
    skills = []
    diffs = []
    lesson_ok = 0
    q_ok = 0
    for it in items:
        lid = it.get("lesson_id")
        if lid is not None:
            lids.append(int(lid))
            if int(lid) in valid_lessons:
                lesson_ok += 1
        qid = it.get("question_id")
        if qid is not None:
            qi = int(qid)
            qids.append(qi)
            if qi in valid_qids:
                q_ok += 1
        r = (it.get("reason") or "").strip()
        reasons.append(len(r))
        sk = it.get("skill_category") or ""
        if sk:
            skills.append(sk)
        df = it.get("difficulty") or ""
        if df:
            diffs.append(df)
    reasons.sort()
    med = reasons[len(reasons) // 2] if reasons else 0
    return {
        "n_questions": n,
        "unique_lessons": len(set(lids)),
        "unique_qids": len(set(qids)),
        "skill_categories": ";".join(sorted(Counter(skills).keys())),
        "avg_reason_chars": sum(reasons) / n,
        "median_reason_chars": float(med),
        "pct_lesson_in_tier": lesson_ok / n,
        "pct_question_in_pool": q_ok / n,
        "difficulty_dist": ";".join(f"{k}:{v}" for k, v in Counter(diffs).most_common()),
    }


def composite_scores(
    diag_words: int,
    quotes: int,
    ex_marks: int,
    lesson_refs: int,
    title_ov: float,
    act: float,
    hw: dict,
) -> tuple[float, float, float]:
    """
    Returns diagnostic_score, homework_score, overall_0_100 (heuristic rubric).
    """
    # Diagnostic: length + evidence of citing data
    depth = min(1.0, diag_words / 350.0)
    quote_ev = min(1.0, (quotes / 3.0) * 0.55 + (min(ex_marks, 8) / 8.0) * 0.45)
    evidence = min(1.0, quote_ev * 0.45 + (min(lesson_refs, 6) / 6.0) * 0.25 + title_ov * 0.30)
    diagnostic_score = 100 * (0.45 * depth + 0.35 * evidence + 0.20 * act)

    # Homework: pool adherence + richness
    pool_adh = 0.5 * hw["pct_lesson_in_tier"] + 0.5 * hw["pct_question_in_pool"]
    richness = min(1.0, hw["avg_reason_chars"] / 120.0) * 0.5 + min(1.0, hw["unique_lessons"] / 8.0) * 0.5
    complete = 1.0 if hw["n_questions"] >= 15 else hw["n_questions"] / 15.0
    homework_score = 100 * (0.55 * pool_adh + 0.30 * richness + 0.15 * complete)

    overall = 0.42 * diagnostic_score + 0.48 * homework_score + 0.10 * (100 if hw["n_questions"] == 15 else 70)
    return diagnostic_score, homework_score, overall


def tier_from_score(s: float) -> str:
    if s >= 82:
        return "A"
    if s >= 72:
        return "B"
    if s >= 60:
        return "C"
    return "D"


def qualitative_vi(
    diagnostic: str,
    hw: dict,
    d_score: float,
    h_score: float,
) -> str:
    parts = []
    if hw["pct_question_in_pool"] >= 0.95 and hw["pct_lesson_in_tier"] >= 0.95:
        parts.append("Bài tập bám chặt question pool.")
    elif hw["pct_question_in_pool"] < 0.85:
        parts.append("Một số câu homework ngoài pool hoặc question_id lệch.")
    dq = count_quoted_fragments(diagnostic) + count_example_markers(diagnostic)
    if word_count(diagnostic) >= 280 and dq >= 2:
        parts.append("Diagnostic có dẫn chứng (trích dẫn/thực tế).")
    elif word_count(diagnostic) < 180:
        parts.append("Diagnostic khá ngắn, ít dẫn chứng cụ thể.")
    if hw["unique_lessons"] <= 2 and hw["n_questions"] >= 10:
        parts.append("Homework tập trung quá ít bài học.")
    if hw["avg_reason_chars"] < 70:
        parts.append("Lý do chọn câu ngắn, ít chi tiết.")
    if not parts:
        parts.append("Cân bằng tốt giữa độ dài diagnostic và giải thích homework.")
    parts.append(f"Điểm heuristic: diagnostic {d_score:.0f}/100, homework {h_score:.0f}/100.")
    return " ".join(parts)


def provider(model: str) -> str:
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    return "unknown"


def main() -> None:
    rows = []
    for student_id in STUDENTS:
        hbm_path = OUTPUT / student_id / "homework_by_model.json"
        if not hbm_path.exists():
            continue
        hbm = load_json(hbm_path)
        valid_lessons, valid_qids, _titles_set, titles_list = build_valid_sets(student_id)
        models = sorted(hbm.get("models", {}).keys())
        for model in models:
            if model in EXCLUDE_MODELS:
                continue
            block = hbm["models"][model]
            diag = block.get("diagnostic") or ""
            hw_items = block.get("homework") or []
            dw = word_count(diag)
            qc = count_quoted_fragments(diag)
            exm = count_example_markers(diag)
            lr = count_lesson_like_refs(diag)
            tov = title_overlap_score(diag, titles_list)
            act = diagnostic_actionability(diag)
            hm = homework_metrics(hw_items, valid_lessons, valid_qids)
            ds, hs, ov = composite_scores(dw, qc, exm, lr, tov, act, hm)
            rows.append({
                "student_id": student_id,
                "model": model,
                "provider": provider(model),
                "diagnostic_chars": len(diag),
                "diagnostic_words": dw,
                "diagnostic_quoted_pairs": qc,
                "diagnostic_example_markers": exm,
                "diagnostic_lesson_like_markers": lr,
                "diagnostic_title_overlap_0_1": round(tov, 3),
                "diagnostic_actionability_0_1": round(act, 3),
                "score_diagnostic_heuristic_0_100": round(ds, 1),
                "homework_question_count": hm["n_questions"],
                "homework_unique_lessons": hm["unique_lessons"],
                "homework_unique_question_ids": hm["unique_qids"],
                "homework_skill_categories": hm["skill_categories"],
                "homework_avg_reason_chars": round(hm["avg_reason_chars"], 1),
                "homework_median_reason_chars": hm["median_reason_chars"],
                "homework_pct_lesson_in_tiered_candidates": round(hm["pct_lesson_in_tier"], 4),
                "homework_pct_question_id_in_pool": round(hm["pct_question_in_pool"], 4),
                "homework_difficulty_distribution": hm["difficulty_dist"],
                "score_homework_heuristic_0_100": round(hs, 1),
                "score_overall_heuristic_0_100": round(ov, 1),
                "tier_overall": tier_from_score(ov),
                "notes_vi": qualitative_vi(diag, hm, ds, hs),
            })

    # Sort for readability: by student, then overall score desc
    rows.sort(key=lambda r: (r["student_id"], -r["score_overall_heuristic_0_100"]))

    # Cross-student mean per model (same 10 models × 3 students after exclusions)
    numeric_keys = [
        "diagnostic_chars",
        "diagnostic_words",
        "diagnostic_quoted_pairs",
        "diagnostic_example_markers",
        "diagnostic_lesson_like_markers",
        "diagnostic_title_overlap_0_1",
        "diagnostic_actionability_0_1",
        "score_diagnostic_heuristic_0_100",
        "homework_question_count",
        "homework_unique_lessons",
        "homework_unique_question_ids",
        "homework_avg_reason_chars",
        "homework_median_reason_chars",
        "homework_pct_lesson_in_tiered_candidates",
        "homework_pct_question_id_in_pool",
        "score_homework_heuristic_0_100",
        "score_overall_heuristic_0_100",
    ]
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)
    agg_rows = []
    for model, lst in sorted(by_model.items()):
        n_st = len(lst)
        agg = {
            "student_id": "__mean_3_students__",
            "model": model,
            "provider": provider(model),
            "homework_skill_categories": "",
            "homework_difficulty_distribution": "",
            "tier_overall": tier_from_score(
                sum(x["score_overall_heuristic_0_100"] for x in lst) / n_st
            ),
            "notes_vi": f"Trung bình cộng {n_st} học sinh (2102555, 2109886, 1585392_newstudent), đã loại gpt-5.4-pro.",
        }
        for k in numeric_keys:
            agg[k] = round(sum(x[k] for x in lst) / n_st, 4 if "pct" in k or "overlap" in k or "actionability" in k else 2)
        agg_rows.append(agg)

    rows.extend(agg_rows)

    out_csv = OUTPUT / "pipeline_diagnostic_homework_quality_analysis.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows → {out_csv}")


if __name__ == "__main__":
    main()
