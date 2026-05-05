# Selector Pool 60-Day Recency Window Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the diagnostic agent’s “lessons to review” view on the full `scored_candidates` timeline (no recency cutoff), while restricting the **homework question pool** passed to the selector to lessons whose `days_since_last_practice` is known and at most 60 days (relative to preprocess `config.TODAY` embedded in each candidate).

**Architecture:** Leave `scripts/preprocess/pipeline.py` and `build_scored_candidates` unchanged so `output/.../student_context.json` remains the full candidate set. In `agents/context_builder.py`, compute one shared **export-eligible enriched list** (candidates that pass the existing question-export gate used by `tier_candidates`). Run the existing greedy **tier selection** on that full list for diagnostic input. Derive **pool lesson IDs** only from enriched candidates that satisfy the recency rule; build `failed_ids_by_lesson` / metadata maps from that recent subset only so selector-facing rows never advertise lessons older than the window.

**Tech Stack:** Python 3, pytest, existing `agents/context_builder.py` (+ minor prompt tweak in `agents/selector_agent.py`).

---

### Task 1: Constants and signal helper

**Files:**
- Modify: `agents/context_builder.py` (module-level constants near `MAX_CANDIDATES`)

**Step 1:** Add:

```python
MAX_SELECTOR_POOL_RECENCY_DAYS = 60
```

**Step 2:** Add a pure function (same logic as today’s inner `_signal` in `tier_candidates`):

```python
def _signal_type_for_candidate(c: dict) -> str:
    if c.get("weakness_score", 0) > 0.5:
        return "critical"
    if (c.get("days_since_last_practice") or 0) > 14:
        return "spaced_rep"
    return "maintenance"
```

**Step 3:** Commit

```bash
git add agents/context_builder.py
git commit -m "feat(agents): add selector pool recency constant and signal helper"
```

---

### Task 2: Extract export-eligible enrichment (shared by tier + pool)

**Files:**
- Modify: `agents/context_builder.py`

**Step 1:** Add `_enriched_export_eligible_candidates(candidates, questions_export, min_questions=MIN_QUESTIONS) -> list[dict]` that:

- Builds `q_map` from `questions_export["lessons"]` the same way `tier_candidates` does today.
- For each `c` in `candidates`, computes `count, _ = _count_usable(lesson)`; if `questions_export` is truthy and `count < min_questions`, skip.
- Otherwise appends `{**c, "signal_type": _signal_type_for_candidate(c), "usable_question_count": count, "skill_coverage": list(set(c.get("weak_skills") or []))}`.

**Step 2:** Refactor `tier_candidates` to call this helper instead of duplicating the enrichment loop; keep the **greedy tier selection** (critical / spaced_rep / maintenance, reserved spaced_rep slots, diversity `_adjusted` scoring) exactly as today, operating on the returned enriched list.

**Step 3:** Run existing tests:

```bash
pytest tests/test_context_builder.py -v
```

Expected: PASS.

**Step 4:** Commit

```bash
git add agents/context_builder.py
git commit -m "refactor(agents): share export-eligible enrichment for tier_candidates"
```

---

### Task 3: Split tiered vs recent pool in `build_context`

**Files:**
- Modify: `agents/context_builder.py` — function `build_context`

**Step 1:** After loading `raw_candidates`, compute:

```python
enriched_all = _enriched_export_eligible_candidates(
    raw_candidates, questions_export, min_questions=MIN_QUESTIONS
)
tiered = _select_tiered_from_enriched(enriched_all, max_candidates=max_candidates)
```

Implement `_select_tiered_from_enriched` by moving the **selection loop** currently at the end of `tier_candidates` into this named function (signature accepts `enriched` list + `max_candidates` + reuse `MIN_SPACED_REP_SLOTS`). Public `tier_candidates` becomes a thin wrapper: `return _select_tiered_from_enriched(_enriched_export_eligible_candidates(...), ...)`.

**Step 2:** Build the recent subset for the selector pool:

```python
recent_enriched = [
    c for c in enriched_all
    if c.get("days_since_last_practice") is not None
    and c["days_since_last_practice"] <= MAX_SELECTOR_POOL_RECENCY_DAYS
]
pool_lesson_ids = {c["lesson_id"] for c in recent_enriched}
```

**Step 3:** Replace maps used **only for pool enrichment**:

- `signal_map`, `days_map`, `weakness_map`, `hw_status_map`: built from `recent_enriched` (not from `tiered`).
- `failed_map` / `failed_ids_by_lesson`: iterate `recent_enriched` only (same inner loop as today over `failed_text_questions`).

**Step 4:** Keep unchanged for diagnostic calibration:

- `_inject_fs_distribution(student_context, raw_candidates)` — still uses full `raw_candidates`.
- `_enrich_candidates_with_speaking(tiered, student_context)` — still on full `tiered` list passed to diagnostic.

**Step 5:** Strip brainstorm speaking types loop stays on `tiered`.

**Step 6:** Call `build_question_pool(pool_lesson_ids, ...)` then attach metadata from the recent maps (same loop as today over `pool`).

**Step 7:** Run:

```bash
pytest tests/test_context_builder.py -v
```

Expected: PASS.

**Step 8:** Commit

```bash
git add agents/context_builder.py
git commit -m "feat(agents): restrict selector question pool to 60-day recency window"
```

---

### Task 4: Failing test — diagnostic tier vs pool recency

**Files:**
- Create: `tests/test_build_context_selector_recency.py`

**Step 1:** Import `build_context` from `agents.context_builder`.

**Step 2:** Build a minimal `student_context`:

```python
{
    "summary": {},
    "lessons": [],  # speaking enrichment optional; empty OK if tiered candidates omit speaking-heavy paths
    "scored_candidates": [
        # Lesson OLD: critical, 90 days ago — must appear in tiered for diagnostic path
        {
            "lesson_id": 9001,
            "title": "Old weak lesson",
            "level": 5,
            "homework_status": "attempted",
            "days_since_last_practice": 90,
            "forgetting_score": 1.0,
            "weakness_score": 0.7,
            "composite_priority_score": 0.99,
            "weak_skills": ["grammar"],
            "failed_text_questions": [{"question_id": 91001, "student_answer": "x", "correct_answer": "y"}],
            "question_bank_preview": [],
            "failed_media_questions_count": 0,
            "worst_speaking_items": [],
            "practice_ids": {"bai_tap": 1, "luyen_tap": 2},
        },
        # Lesson NEW: weaker priority but inside 60d — must contribute pool rows only if export has questions
        {
            "lesson_id": 9002,
            "title": "Recent lesson",
            "level": 5,
            "homework_status": "attempted",
            "days_since_last_practice": 10,
            "forgetting_score": 0.3,
            "weakness_score": 0.55,
            "composite_priority_score": 0.5,
            "weak_skills": ["grammar"],
            "failed_text_questions": [{"question_id": 92001, "student_answer": "a", "correct_answer": "b"}],
            "question_bank_preview": [],
            "failed_media_questions_count": 0,
            "worst_speaking_items": [],
            "practice_ids": {"bai_tap": 3, "luyen_tap": 4},
        },
    ],
}
```

**Step 3:** Build `questions_export` with **two lessons** matching `9001` and `9002`, each with **≥2 usable homework questions** (copy/adapt minimal structure from `tests/test_context_builder.py` `QUESTIONS_EXPORT`).

**Step 4:** Assertions:

```python
tiered, pool = build_context(student_context, questions_export)
tiered_ids = {c["lesson_id"] for c in tiered}
assert 9001 in tiered_ids, "diagnostic tier should still surface old weak lesson"
pool_lesson_ids = {q["lesson_id"] for q in pool}
assert 9001 not in pool_lesson_ids, "selector pool must exclude lesson beyond recency window"
assert 9002 in pool_lesson_ids or len(pool_lesson_ids) == 0  # if export malformed, adjust fixture until non-empty
```

Tighten so `9002` is definitely in pool (adjust scores/export so recent lesson keeps ≥2 questions).

**Step 5:** Add boundary test via third lesson `days_since_last_practice == 60` → allowed in pool; `61` → excluded.

**Step 6:** Run:

```bash
pytest tests/test_build_context_selector_recency.py -v
```

Expected: PASS after Task 3 implementation.

**Step 7:** Run full suite:

```bash
pytest tests/ -q
```

**Step 8:** Commit

```bash
git add tests/test_build_context_selector_recency.py
git commit -m "test(agents): cover build_context diagnostic vs selector recency split"
```

---

### Task 5: Selector prompt example (avoid &gt;60d few-shot clash)

**Files:**
- Modify: `agents/selector_agent.py` — `SYSTEM_PROMPT` REASON FIELD RULES example sentence

**Step 1:** Replace the illustrative `"118 ngày trước"` example with something ≤60 days (e.g. `"34 ngày trước"`) and add one sentence: pool lines only carry recency within the configured window — reasons must match the `{N}d ago` shown on the pool line.

**Step 2:** Commit

```bash
git add agents/selector_agent.py
git commit -m "fix(agents): align selector reason example with pool recency window"
```

---

### Task 6: Optional diagnostic prompt note (product clarity)

**Files:**
- Modify: `agents/diagnostic_agent.py` — `SYSTEM_PROMPT` (one short paragraph)

**Step 1:** State explicitly that homework selection draws only from lessons recent enough to appear in the selector pool (students may still see analysis of older weak lessons without those lessons appearing in tonight’s worksheet).

**Step 2:** Commit (skip if product prefers shorter system prompt).

---

### Task 7: Docs cleanup

**Files:**
- Modify: `docs/plans/2026-05-05-homework-candidate-60-day-window-design.md` (align “Decision” with selector-only pool filter)
- Modify: `docs/plans/2026-05-05-homework-candidate-60-day-window.md` → replace body with pointer to this file **or** delete after confirming no external links

**Step 1:** Update design doc Problem/Decision to match split responsibility.

**Step 2:** Commit

```bash
git add docs/plans/
git commit -m "docs: align 60-day window design with selector-only filtering"
```

---

## Operational notes

- **Anchor date:** `days_since_last_practice` comes from preprocess relative to `scripts/preprocess/config.TODAY`. Operators must keep `TODAY` realistic when regenerating `student_context.json`; the selector window moves with that anchor.
- **Empty pool:** If no candidate satisfies export gate + recency, `question_pool` may be empty — pipeline should fail loudly (existing behavior). Do not widen the window automatically.

---

**Plan complete** — saved as `docs/plans/2026-05-05-selector-pool-recency-window.md`.

**Execution options:**

1. **Subagent-driven (session này)** — làm từng task, review giữa các bước (@superpowers:subagent-driven-development).

2. **Session riêng** — mở session mới với @superpowers:executing-plans theo checklist.

Bạn muốn triển khai theo hướng nào?
