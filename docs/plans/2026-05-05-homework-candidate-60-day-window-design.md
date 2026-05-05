# Homework candidate window (60 days) — design

**Date:** 2026-05-05  
**Status:** Approved

## Problem

The homework agent pipeline draws exercises from `scored_candidates` in `student_context.json`. Lessons whose last activity is very old still appear in the pool, which pulls homework too far back in the curriculum timeline.

## Decision

1. Only include candidates whose **last practice activity** is known and falls within the **last 60 days** (inclusive at day 60), measured against `scripts/preprocess/config.TODAY`.
2. If `days_since_last_practice` is **missing** (`null`), **exclude** the candidate from the homework pool (option B).

## Approach

Apply filtering in **`build_scored_candidates`** in `scripts/preprocess/pipeline.py`, after each candidate dict is assembled and **before** score-threshold pooling (`MIN_CANDIDATE_SCORE`, fallback, `MAX_CANDIDATE_POOL_SIZE`). This keeps a single authoritative pool for CLI agents, web homework flows, and tiering.

Configuration: **`MAX_DAYS_SINCE_LAST_PRACTICE = 60`** in `scripts/preprocess/config.py`.

## Edge cases

- **Empty or tiny pool after filter:** Do not relax the window to include older lessons. Preserve existing behavior when the pool is empty (pipeline errors / no tiering).
- Optional: log how many candidates were dropped for the date window (nice-to-have; keep minimal).

## Testing

Add unit tests with synthetic candidate-shaped dicts or by calling `build_scored_candidates` with stub `records` covering: `days_since` null, `> 60`, and `≤ 60` (within other minimum gates).

## Out of scope

- Changing how `days_since_last_practice` is computed.
- Separate “full history” export in JSON (YAGNI unless requested).
