# Remove brainstorm signal from all pipelines

**Date:** 2026-05-05  
**Status:** Approved  
**Scope:** Option B — remove brainstorm entirely from aggregates, critical flags, agent context, exports, API, UI, and evaluation (no replacement “shadow” stats).

## Problem

Brainstorm-style Digital Teacher items (image → target vocabulary) are judged unreliable as a learning signal. They should not influence homework selection, diagnostics, speaking quotas, or user-visible history.

## Decision

- **Remove** all `brainstorm`-specific fields and buckets from `student_context`, `questions_export`, backend JSON, and frontend presentation.
- **Replace** `min_speaking` / emphasis logic that used `overall_brainstorm_score_avg` with the same thresholds applied to **`overall_free_speaking_score_avg`** (from warmup / free_speaking only). Treat `None` as 100 (same as prior brainstorm default).
- **Weakness score** (`compute_weakness_score`): spoken component uses only `free_speaking_score_avg` (no `min(free, brainstorm)`). Pronunciation fallback when participated but no free speaking remains.
- **`critical_speaking_types`**: drop `brainstorm`; keep `free_speaking` when global free average &lt; 50.
- **`worst_speaking_items`**: exclude failed brainstorm turns so they never appear in diagnostic samples.
- **Internal classification** (`classify_audio` → `"brainstorm"`) may remain for code clarity but **must not** produce user- or agent-visible outputs.

## Components touched (summary)

| Area | Change |
|------|--------|
| `scripts/preprocess/digital_teacher.py` | No brainstorm aggregates; no brainstorm in failed-speaking merge; simplify `_build_speaking_item` brainstorm-only fields if unused |
| `scripts/preprocess/pipeline.py` | Drop `overall_brainstorm_*`; drop brainstorm from `critical_speaking`; CLI print |
| `scripts/export_questions/*` | Remove `extract_brainstorm`, bucket, stats |
| `agents/context_builder.py` | No brainstorm pool items; no `brainstorm_*` in `speaking_scores` |
| `agents/diagnostic_agent.py` | Remove brainstorm instructions and template placeholders |
| `agents/selector_agent.py` | Remove brainstorm examples from prompts |
| `scripts/agent_pipeline.py`, `web/backend/pipeline_ws.py` | `min_speaking` from free speaking avg |
| `scripts/evaluate/*` | Renamed / free-speaking-based signals in reports and LLM judge |
| `web/backend/routers/lessons.py`, `history.py` | Omit brainstorm fields |
| `web/frontend` | Remove Brainstorm sections, metrics, counts |
| `tests/*` | Update assertions |

## Compatibility

Older `student_context.json` may still contain brainstorm keys; new runs omit them. Recommend rerunning preprocess + export for active students.

## Out of scope

Changing LMS question types, Mongo raw exports, or Digital Teacher product behavior — only this repository’s derived artifacts and agents.
