"""
Pre-filter and tier scored_candidates before sending to LLM agents.

Tiering rules:
  critical    weakness_score > 0.5
  spaced_rep  days_since > 14 AND weakness_score <= 0.5
  maintenance everything else

Selection: greedy within each tier, sorted by composite_priority_score DESC.
Skill-diversity boost: +0.1 per new skill category not yet covered.
Cap: MAX_CANDIDATES total across all tiers.

Question pool includes plain-text items and media-dependent LMS items (stub
question_text when the stem is image/audio-only) so the selector can assign
a bounded number of media questions.
"""

from __future__ import annotations

MAX_CANDIDATES = 15
MIN_QUESTIONS = 2  # lessons with fewer usable questions are excluded

# Shown in pool / homework when stem is mostly image+audio (no plain text stem).
MEDIA_QUESTION_TEXT_STUB = (
    "[Câu có hình/âm thanh — mở bài trên LMS hoặc xem phần đính kèm bên dưới]"
)


def _poolable_practice_question(q: dict) -> bool:
    """Text-only needs question_text; media needs question_id or text or at least one stem URL."""
    if q.get("requires_media"):
        return bool(
            q.get("question_id") is not None
            or (q.get("question_text") or "").strip()
            or (q.get("stem_media_urls") or [])
        )
    return bool((q.get("question_text") or "").strip())


def _normalize_practice_row_for_pool(q: dict, source: str) -> dict | None:
    """Copy row into pool shape; ensure non-empty question_text for LLM + strict JSON."""
    if not _poolable_practice_question(q):
        return None
    row = {**q, "source": source}
    row.setdefault("stem_media_urls", [])
    row.setdefault("comment_media_urls", [])
    if not (row.get("question_text") or "").strip():
        if row.get("requires_media"):
            row["question_text"] = MEDIA_QUESTION_TEXT_STUB
        else:
            return None
    return row


def _count_usable(lesson: dict) -> tuple[int, list]:
    """Return (count, list) of poolable questions (plain text + media-dependent)."""
    usable = []
    hw = lesson.get("homework") or {}
    for ptype in ("bai_tap", "luyen_tap"):
        practice = hw.get(ptype) or {}
        for q in practice.get("questions") or []:
            norm = _normalize_practice_row_for_pool(q, ptype)
            if norm is not None:
                usable.append(norm)
    ic = lesson.get("in_class") or {}
    for item in ic.get("free_speaking") or []:
        if item.get("question"):
            usable.append({
                "question_id": None,
                "question_folder": "Speaking",
                "question_type": item.get("question_type", "free_speaking"),
                "question_text": item["question"],
                "requires_media": False,
                "correct_answer": None,
                "interaction_type": "free_speaking",
                "source": "in_class",
            })
    for item in ic.get("brainstorm") or []:
        if item.get("question"):
            usable.append({
                "question_id": None,
                "question_folder": "Speaking",
                "question_type": item.get("question_type", "brainstorm"),
                "question_text": item["question"],
                "requires_media": False,
                "correct_answer": None,
                "interaction_type": "brainstorm",
                "source": "in_class",
            })
    return len(usable), usable


def tier_candidates(
    candidates: list,
    questions_export: dict | None = None,
    min_questions: int = MIN_QUESTIONS,
    max_candidates: int = MAX_CANDIDATES,
) -> list:
    """
    Assign signal_type to each candidate, filter by question availability,
    apply diversity-aware greedy selection, cap at max_candidates.
    """
    q_map = {}
    if questions_export:
        q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}

    def _signal(c):
        if c.get("weakness_score", 0) > 0.5:
            return "critical"
        if (c.get("days_since_last_practice") or 0) > 14:
            return "spaced_rep"
        return "maintenance"

    enriched = []
    for c in candidates:
        signal = _signal(c)
        lesson = q_map.get(c["lesson_id"], {})
        count, _ = _count_usable(lesson)
        if questions_export and count < min_questions:
            continue
        enriched.append({
            **c,
            "signal_type": signal,
            "usable_question_count": count,
            "skill_coverage": list(set(c.get("weak_skills") or [])),
        })

    tier_order = ["critical", "spaced_rep", "maintenance"]
    selected = []
    covered_skills = set()

    for tier in tier_order:
        if len(selected) >= max_candidates:
            break
        remaining = [c for c in enriched if c["signal_type"] == tier]
        while remaining and len(selected) < max_candidates:
            # Re-score against current covered_skills so diversity boost is accurate
            for c in remaining:
                new_skills = set(c.get("weak_skills") or []) - covered_skills
                c["_adjusted"] = c["composite_priority_score"] + 0.1 * len(new_skills)
            best = max(remaining, key=lambda c: c["_adjusted"])
            selected.append(best)
            covered_skills.update(best.get("weak_skills") or [])
            remaining.remove(best)

    # Clean up internal field
    for c in selected:
        c.pop("_adjusted", None)

    return selected


def build_question_pool(lesson_ids: set, questions_export: dict) -> list:
    """
    Flatten usable questions from the given lesson_ids.
    Attaches lesson_id, lesson_title, signal_type (from tiered_candidates if available).
    """
    q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}
    pool = []
    for lid in lesson_ids:
        lesson = q_map.get(lid, {})
        _, usable = _count_usable(lesson)
        title = lesson.get("title", "")
        for q in usable:
            pool.append({
                "lesson_id": lid,
                "lesson_title": title,
                "signal_type": None,  # caller sets this after tier_candidates
                **q,
            })
    return pool


def build_context(
    student_context: dict,
    questions_export: dict,
    max_candidates: int = MAX_CANDIDATES,
) -> tuple[list, list]:
    """
    Main entry: returns (tiered_candidates, question_pool).
    tiered_candidates: enriched candidate list with signal_type
    question_pool: flat list of usable questions from those lessons
    """
    raw_candidates = student_context.get("scored_candidates", [])
    tiered = tier_candidates(
        raw_candidates,
        questions_export,
        max_candidates=max_candidates,
    )

    signal_map = {c["lesson_id"]: c["signal_type"] for c in tiered}
    days_map = {c["lesson_id"]: c.get("days_since_last_practice") for c in tiered}
    weakness_map = {c["lesson_id"]: c.get("weakness_score") for c in tiered}
    hw_status_map = {c["lesson_id"]: c.get("homework_status") for c in tiered}
    lesson_ids = set(signal_map.keys())
    pool = build_question_pool(lesson_ids, questions_export)
    for q in pool:
        lid = q["lesson_id"]
        q["signal_type"] = signal_map.get(lid)
        q["days_since"] = days_map.get(lid)
        q["weakness_score"] = weakness_map.get(lid)
        q["hw_status"] = hw_status_map.get(lid)

    return tiered, pool
