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

Pool pre-filtering: at most MAX_POOL_PER_LESSON questions per lesson are sent to
the selector, chosen greedily for diversity (non-media first, then varied types).
"""

from __future__ import annotations

MAX_CANDIDATES = 15
MIN_SPACED_REP_SLOTS = 2  # reserved slots for spaced_rep tier when available
MIN_QUESTIONS = 2  # lessons with fewer usable questions are excluded
MAX_POOL_PER_LESSON = 5  # cap questions per lesson sent to selector
MAX_SELECTOR_POOL_RECENCY_DAYS = 60  # pool for selector: only lessons practiced within this window

# Shown in pool / homework when stem is mostly image+audio (no plain text stem).
MEDIA_QUESTION_TEXT_STUB = (
    "[Câu có hình/âm thanh — mở bài trên LMS hoặc xem phần đính kèm bên dưới]"
)

# Map Vietnamese question types → English skill_hint for the selector
_SKILL_HINT_MAP: dict[str, str] = {
    "Điền vào chỗ trống": "grammar",
    "Sắp xếp câu": "grammar",
    "Sắp xếp từ": "grammar",
    "Nối từ": "grammar",
    "Kéo thả": "grammar",
    "Trả lời bằng giọng nói": "speaking",
    "free_speaking": "speaking",
    "Một lựa chọn": "vocabulary",
    "Nhiều lựa chọn": "vocabulary",
}


def _skill_hint(q: dict) -> str:
    """Infer skill category from question type and folder."""
    qtype = q.get("question_type", "")
    folder = q.get("question_folder", "")
    source = q.get("source", "")
    interaction = q.get("interaction_type", "")

    if source == "in_class" or interaction == "free_speaking":
        return "speaking"
    if "Trả lời bằng giọng nói" in qtype:
        return "speaking"
    if any(k in qtype for k in ("Điền", "Sắp xếp", "Kéo thả", "Nối")):
        return "grammar"
    if "Từ vựng" in folder or "vocabulary" in folder.lower():
        return "vocabulary"
    hint = _SKILL_HINT_MAP.get(qtype)
    if hint:
        return hint
    return "other"


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
    return len(usable), usable


def _filter_pool_for_lesson(
    questions: list,
    max_per_lesson: int,
    failed_question_ids: set | None = None,
) -> list:
    """
    Select up to max_per_lesson representative questions for one lesson.

    Priority order (greedy for skill diversity):
      0. Previously-failed questions (from homework/practice results) — always pinned first
      1. Non-media questions with plain question_text (most usable offline)
      2. Media questions that have a comment_plain (at least some context)
      3. Remaining media questions

    Within each tier we pick greedily to maximise skill_hint diversity.
    """
    failed_ids: set = failed_question_ids or set()

    def _priority(q: dict) -> int:
        if q.get("question_id") in failed_ids:
            return -1  # pin failed questions first
        if not q.get("requires_media"):
            return 0
        if (q.get("comment_plain") or "").strip():
            return 1
        return 2

    sorted_qs = sorted(questions, key=_priority)
    selected: list[dict] = []
    covered_skills: set[str] = set()

    for q in sorted_qs:
        if len(selected) >= max_per_lesson:
            break
        hint = _skill_hint(q)
        # Always include the first question of a new skill type; after that
        # allow duplicates only when we still have room.
        if hint not in covered_skills or len(selected) < max_per_lesson:
            selected.append(q)
            covered_skills.add(hint)

    return selected[:max_per_lesson]


def _signal_type_for_candidate(c: dict) -> str:
    """Map a scored candidate to its tier label."""
    if c.get("weakness_score", 0) > 0.5:
        return "critical"
    if (c.get("days_since_last_practice") or 0) > 14:
        return "spaced_rep"
    return "maintenance"


def _enriched_export_eligible_candidates(
    candidates: list,
    questions_export: dict | None = None,
    min_questions: int = MIN_QUESTIONS,
) -> list:
    """
    Attach signal_type / usable_question_count / skill_coverage to each candidate
    and filter out lessons that lack enough usable questions in the export.
    Returns all candidates that pass the gate (no tier selection yet).
    """
    q_map = {}
    if questions_export:
        q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}

    enriched = []
    for c in candidates:
        lesson = q_map.get(c["lesson_id"], {})
        count, _ = _count_usable(lesson)
        if questions_export and count < min_questions:
            continue
        enriched.append({
            **c,
            "signal_type": _signal_type_for_candidate(c),
            "usable_question_count": count,
            "skill_coverage": list(set(c.get("weak_skills") or [])),
        })
    return enriched


def _select_tiered_from_enriched(
    enriched: list,
    max_candidates: int = MAX_CANDIDATES,
) -> list:
    """
    Greedy tier selection over an already-enriched candidate list.
    Applies critical/spaced_rep/maintenance ordering with diversity boost.
    """
    # Reserve MIN_SPACED_REP_SLOTS slots for spaced_rep so it always appears in the pool.
    # Without this, 28 critical candidates would fill all 15 slots before spaced_rep is seen.
    spaced_rep_available = sum(1 for c in enriched if c["signal_type"] == "spaced_rep")
    reserved = min(MIN_SPACED_REP_SLOTS, spaced_rep_available)
    critical_cap = max_candidates - reserved  # critical fills up to this many slots

    tier_order = ["critical", "spaced_rep", "maintenance"]
    selected = []
    covered_skills: set = set()

    for tier in tier_order:
        if len(selected) >= max_candidates:
            break
        tier_limit = critical_cap if tier == "critical" else max_candidates
        remaining = [c for c in enriched if c["signal_type"] == tier]
        while remaining and len(selected) < tier_limit:
            # Re-score against current covered_skills so diversity boost is accurate
            for c in remaining:
                new_skills = set(c.get("weak_skills") or []) - covered_skills
                c["_adjusted"] = c["composite_priority_score"] + 0.1 * len(new_skills)
            best = max(remaining, key=lambda c: c["_adjusted"])
            selected.append(best)
            covered_skills.update(best.get("weak_skills") or [])
            remaining.remove(best)

    for c in selected:
        c.pop("_adjusted", None)

    return selected


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
    enriched = _enriched_export_eligible_candidates(candidates, questions_export, min_questions)
    return _select_tiered_from_enriched(enriched, max_candidates)


def build_question_pool(
    lesson_ids: set,
    questions_export: dict,
    max_per_lesson: int = MAX_POOL_PER_LESSON,
    failed_ids_by_lesson: dict[int, set] | None = None,
) -> list:
    """
    Flatten usable questions from the given lesson_ids.
    Applies per-lesson cap via _filter_pool_for_lesson for manageable pool size.
    Attaches lesson_id, lesson_title, signal_type (caller sets after tier_candidates).

    failed_ids_by_lesson: mapping lesson_id → set of question_ids the student
    previously answered incorrectly. These are pinned to the front of each
    lesson's pool so the LLM sees them and can assign prev_wrong evidence.
    """
    q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}
    pool = []
    for lid in lesson_ids:
        lesson = q_map.get(lid, {})
        _, usable = _count_usable(lesson)
        failed_ids = (failed_ids_by_lesson or {}).get(lid)
        filtered = _filter_pool_for_lesson(usable, max_per_lesson, failed_ids)
        title = lesson.get("title", "")
        for q in filtered:
            pool.append({
                "lesson_id": lid,
                "lesson_title": title,
                "signal_type": None,  # caller sets this after tier_candidates
                "skill_hint": _skill_hint(q),
                **q,
            })
    return pool


def _enrich_candidates_with_speaking(
    tiered: list,
    student_context: dict,
) -> None:
    """
    Attach per-lesson speaking averages from student_context['lessons'] to each
    tiered candidate in-place. Fills speaking_scores dict with available metrics.
    """
    lessons_by_id = {l["lesson_id"]: l for l in student_context.get("lessons", [])}
    for c in tiered:
        lesson = lessons_by_id.get(c["lesson_id"], {})
        ic = lesson.get("in_class", {})
        c["speaking_scores"] = {
            "free_speaking_avg": ic.get("free_speaking_score_avg"),
            "free_speaking_attempts": ic.get("free_speaking_attempts", 0),
            "conversation_avg": ic.get("conversation_score_avg"),
            "conversation_attempts": ic.get("conversation_attempts", 0),
            "pronunciation_avg": ic.get("pronunciation_score_avg"),
            "pronunciation_attempts": ic.get("pronunciation_attempts", 0),
        }


def _inject_fs_distribution(student_context: dict, raw_candidates: list) -> None:
    """
    Compute free_speaking lesson distribution across ALL scored_candidates and
    inject it into student_context['summary'] as 'free_speaking_lesson_dist'.

    This gives the diagnostic agent a calibrated baseline: the "lessons to review"
    are deliberately the weakest ones, so fs=0 there is expected. The full
    distribution (good/partial/zero) prevents over-generalization.
    """
    lessons_by_id = {l["lesson_id"]: l for l in student_context.get("lessons", [])}
    fs_good = fs_partial = fs_zero = 0
    for c in raw_candidates:
        lid = c.get("lesson_id")
        lesson = lessons_by_id.get(lid, {})
        ic = lesson.get("in_class", {})
        fa = ic.get("free_speaking_attempts", 0)
        if fa == 0:
            continue
        avg = ic.get("free_speaking_score_avg")
        if avg is None:
            continue
        if avg == 0:
            fs_zero += 1
        elif avg >= 0.8:
            fs_good += 1
        else:
            fs_partial += 1
    student_context.setdefault("summary", {})["free_speaking_lesson_dist"] = {
        "good": fs_good,
        "partial": fs_partial,
        "zero": fs_zero,
        "total": fs_good + fs_partial + fs_zero,
    }


def build_context(
    student_context: dict,
    questions_export: dict,
    max_candidates: int = MAX_CANDIDATES,
    max_pool_per_lesson: int = MAX_POOL_PER_LESSON,
) -> tuple[list, list]:
    """
    Main entry: returns (tiered_candidates, question_pool).
    tiered_candidates: enriched candidate list with signal_type + speaking_scores
    question_pool: filtered list of representative questions from those lessons
    """
    raw_candidates = student_context.get("scored_candidates", [])

    # Enrich all export-eligible candidates once; reuse for both tier selection and pool.
    enriched_all = _enriched_export_eligible_candidates(
        raw_candidates, questions_export, min_questions=MIN_QUESTIONS
    )

    # --- Diagnostic path: full tiered list, no recency cutoff ---
    tiered = _select_tiered_from_enriched(enriched_all, max_candidates=max_candidates)
    _enrich_candidates_with_speaking(tiered, student_context)

    # Inject free_speaking lesson distribution across ALL scored_candidates into the
    # summary so the diagnostic agent can calibrate its assessment against selection bias.
    # "Lessons to review" are the WEAKEST lessons — fs=0 there is expected; the summary
    # must show the full picture to avoid overgeneralizing.
    _inject_fs_distribution(student_context, raw_candidates)

    # Strip brainstorm items from worst_speaking_items before sending to LLM agents.
    # brainstorm is an open-ended vocabulary recall task — its transcripts are not
    # interpretable as grammar/speaking evidence the way conversation/free_speaking are.
    # This guard handles stale student_context.json files generated before the filter
    # was added to build_dt_in_class / build_scored_candidates.
    _VALID_SPEAKING_TYPES = {"free_speaking", "conversation"}
    for c in tiered:
        if c.get("worst_speaking_items"):
            c["worst_speaking_items"] = [
                w for w in c["worst_speaking_items"]
                if w.get("lms_type") in _VALID_SPEAKING_TYPES
            ]

    # --- Selector pool path: only lessons with recent activity (≤ window days) ---
    recent_enriched = [
        c for c in enriched_all
        if c.get("days_since_last_practice") is not None
        and c["days_since_last_practice"] <= MAX_SELECTOR_POOL_RECENCY_DAYS
    ]
    pool_lesson_ids = {c["lesson_id"] for c in recent_enriched}

    signal_map = {c["lesson_id"]: c["signal_type"] for c in recent_enriched}
    days_map = {c["lesson_id"]: c.get("days_since_last_practice") for c in recent_enriched}
    weakness_map = {c["lesson_id"]: c.get("weakness_score") for c in recent_enriched}
    hw_status_map = {c["lesson_id"]: c.get("homework_status") for c in recent_enriched}

    # Build per-question map of previously failed attempts: (lesson_id, question_id) → answers
    failed_map: dict[tuple, dict] = {}
    failed_ids_by_lesson: dict[int, set] = {}
    for c in recent_enriched:
        lid = c["lesson_id"]
        for fq in c.get("failed_text_questions", []):
            qid = fq["question_id"]
            failed_map[(lid, qid)] = {
                "prev_student_answer": fq.get("student_answer"),
                "prev_correct_answer": fq.get("correct_answer"),
            }
            failed_ids_by_lesson.setdefault(lid, set()).add(qid)

    pool = build_question_pool(
        pool_lesson_ids,
        questions_export,
        max_per_lesson=max_pool_per_lesson,
        failed_ids_by_lesson=failed_ids_by_lesson,
    )
    for q in pool:
        lid = q["lesson_id"]
        qid = q.get("question_id")
        q["signal_type"] = signal_map.get(lid)
        q["days_since"] = days_map.get(lid)
        q["weakness_score"] = weakness_map.get(lid)
        q["hw_status"] = hw_status_map.get(lid)
        if qid and (lid, qid) in failed_map:
            q.update(failed_map[(lid, qid)])

    return tiered, pool
