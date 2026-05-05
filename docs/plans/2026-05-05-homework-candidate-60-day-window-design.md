# Selector pool recency (60 days) — design

**Date:** 2026-05-05  
**Status:** Approved (revised)

## Problem

Homework selection should prefer exercises tied to **recent** practice (within ~60 days). Earlier drafts filtered candidates in preprocess, which would also shrink what the diagnostic agent sees.

## Decision (revised)

1. **Diagnostic agent:** Continues to receive **`tier_candidates`** built from the full `scored_candidates` list (same export-eligible gate as today). No recency cutoff — old weak lessons can still appear in “lessons to review”.
2. **Selector agent:** Receives a **question pool** built only from lessons where `days_since_last_practice` is **known** and **≤ 60** (inclusive), relative to preprocess `config.TODAY` reflected in each candidate.
3. **Preprocess / `student_context.json`:** **Unchanged** — full candidate pool remains for history, APIs, and diagnostic context.

## Implementation location

- **`agents/context_builder.py` — `build_context`:** After computing export-eligible enriched candidates, run tier selection on the full enriched set for diagnostic; derive pool lesson IDs and pool metadata maps from the **recent** subset only.
- **Constant:** `MAX_SELECTOR_POOL_RECENCY_DAYS = 60` in `agents/context_builder.py` (selector concern, not LMS preprocess).

## Edge cases

- **Empty recent pool:** Do not relax the window. Pipeline may fail if there is no export-eligible lesson within 60 days — acceptable.
- **Narrative vs homework:** Diagnostic may discuss an old lesson that does not appear in the selector pool; optional short note in diagnostic system prompt (see implementation plan Task 6).

## Testing

- `build_context` integration test: tiered includes a lesson with `days_since > 60`; pool contains no questions for that lesson; recent lesson appears in pool.

## Out of scope

- Dynamic “today” in preprocess (still uses `config.TODAY`).
- Changing tier size (`MAX_CANDIDATES`) or scoring formulas.

**Implementation plan:** [2026-05-05-selector-pool-recency-window.md](./2026-05-05-selector-pool-recency-window.md)
