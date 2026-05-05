# Homework Candidate 60-Day Window Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restrict `scored_candidates` to lessons with a known last activity within the last 60 days (`config.TODAY`), excluding candidates with missing `days_since_last_practice`.

**Architecture:** Add `MAX_DAYS_SINCE_LAST_PRACTICE` in preprocess config. After building each homework candidate in `build_scored_candidates`, filter out rows where `days_since_last_practice` is `None` or greater than the configured maximum, before applying score thresholds and pool caps.

**Tech Stack:** Python 3, pytest, existing `scripts/preprocess/` package.

---

### Task 1: Configuration constant

**Files:**
- Modify: `scripts/preprocess/config.py`

**Step 1:** Insert after `MIN_CANDIDATE_POOL_FALLBACK` (or adjacent constants):

```python
MAX_DAYS_SINCE_LAST_PRACTICE = 60
```

**Step 2:** Commit

```bash
git add scripts/preprocess/config.py
git commit -m "feat(preprocess): add MAX_DAYS_SINCE_LAST_PRACTICE window constant"
```

---

### Task 2: Filter candidates by activity window

**Files:**
- Modify: `scripts/preprocess/pipeline.py` — function `build_scored_candidates`

**Step 1:** After the list comprehension that drops candidates without usable signals (the block ending around line 163 that filters `failed_text_questions`, `question_bank_preview`, etc.), insert:

```python
    candidates = [
        c
        for c in candidates
        if c.get("days_since_last_practice") is not None
        and c["days_since_last_practice"] <= config.MAX_DAYS_SINCE_LAST_PRACTICE
    ]
```

Place this **before** the `above = [...]` line that splits by `MIN_CANDIDATE_SCORE`.

**Step 2:** Optional one-line diagnostic after the filter (YAGNI-friendly): only add if you want visibility, e.g. `print(f\"  Candidates after {config.MAX_DAYS_SINCE_LAST_PRACTICE}d window: {len(candidates)}\")` next to existing prints in `build_student_context` / `main` — skip if noisy.

**Step 3:** Commit

```bash
git add scripts/preprocess/pipeline.py
git commit -m "feat(preprocess): restrict scored_candidates to recent activity window"
```

---

### Task 3: Unit tests for the date window

**Files:**
- Create: `tests/test_preprocess_candidate_window.py`

**Step 1:** Write tests that call `build_scored_candidates` with minimal fake `records` matching the structure expected by that function (see `scripts/preprocess/pipeline.py` — each record needs `status`, `homework`, `in_class`, scoring fields, etc.).

Minimal pattern: build three records that all pass the “has signal” gates (e.g. each with `failed_text_questions` non-empty via `homework`) but differ in `days_since_last_practice`:

- `None` → must not appear in returned pool
- `61` → must not appear
- `30` → must appear (assuming `composite_priority_score` still passes downstream filters)

Reuse the shape from `tests/test_context_builder.py` candidate dicts where possible, but `build_scored_candidates` expects **records**, not scored candidate dicts. Easiest approach: construct minimal `records` list:

```python
def _minimal_record(days_since, has_failed_q=True):
    failed = [{"q": 1}] if has_failed_q else []
    hw = {
        "attempted": True,
        "worst_questions": failed,
        "lms_ids": {"bai_tap": 1, "luyen_tap": 2},
        "bai_tap": {"practice_id": 1},
        "luyen_tap": {"practice_id": 2},
        "weak_skills": [],
    }
    return {
        "lesson_id": id(...),  # use unique int per call
        "title": "t",
        "level": 1,
        "status": "completed",
        "last_activity_date": "2026-04-01",
        "days_since_last_practice": days_since,
        "forgetting_score": 0.5,
        "weakness_score": 0.6,
        "composite_priority_score": 0.95,
        "in_class": {"worst_speaking_items": []},
        "homework": hw,
    }
```

Adjust field names to match exactly what `build_scored_candidates` reads.

**Step 2:** Run tests

```bash
pytest tests/test_preprocess_candidate_window.py -v
```

Expected: PASS after implementation.

**Step 3:** Run full suite

```bash
pytest tests/ -q
```

Expected: all pass.

**Step 4:** Commit

```bash
git add tests/test_preprocess_candidate_window.py
git commit -m "test(preprocess): cover 60-day candidate window filtering"
```

---

### Task 4: Regenerate student context (manual verification)

**Files:** none (artifact only)

**Step 1:** From repo root:

```bash
python preprocess.py
```

**Step 2:** Inspect `output/student_context.json`: `scored_candidates` entries should all have `days_since_last_practice` ≤ 60.

**Step 3:** Do not commit generated JSON unless your workflow normally tracks it.

---

**Plan complete.** Use executing-plans (or implement inline) task-by-task.
