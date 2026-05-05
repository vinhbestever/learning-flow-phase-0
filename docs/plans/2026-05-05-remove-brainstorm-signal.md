# Remove brainstorm signal — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strip all Digital Teacher “brainstorm” vocabulary-from-image signal from preprocess, exports, agent context, diagnostics, min_speaking, evaluate tooling, API, and frontend; use free_speaking averages for speaking quotas where brainstorm was used.

**Architecture:** Delete or stop emitting brainstorm branches in `digital_teacher` and `pipeline` summaries; remove export and `context_builder` pool entries; retarget `min_speaking` and evaluate “emphasis” checks to `overall_free_speaking_score_avg`; clean prompts and UI. See `docs/plans/2026-05-05-remove-brainstorm-signal-design.md`.

**Tech stack:** Python 3, FastAPI backend, React/TS frontend, pytest.

---

### Task 1: Preprocess — in-class metrics and weakness

**Files:**
- Modify: `scripts/preprocess/digital_teacher.py`
- Modify: `scripts/preprocess/pipeline.py`

**Step 1:** Remove brainstorm aggregation blocks (`brainstorm_items`, scores, `brainstorm_answer_type_dist`), remove brainstorm from `all_failed` / `worst_speaking_items`. Remove brainstorm keys from returned `in_class` dict.

**Step 2:** In `_build_speaking_item`, remove `target_objects` / `correct_objects` / brainstorm-only branches if nothing else sets them; keep fields only if other `lms_type` values need them.

**Step 3:** Update `compute_weakness_score`: drop `brainstorm_score_avg`; use only `free_speaking_score_avg` for the spoken weighted term (keep pron fallback).

**Step 4:** In `pipeline.build_summary`, remove `all_brain_*`, `brain_avg`, `critical_speaking` entry for brainstorm, `overall_brainstorm_*` keys, and brainstorm CLI print line.

**Step 5:** Commit — `git add scripts/preprocess/digital_teacher.py scripts/preprocess/pipeline.py && git commit -m "refactor(preprocess): drop brainstorm metrics from in-class and summary"`

---

### Task 2: Export questions

**Files:**
- Modify: `scripts/export_questions/in_class.py` (delete `extract_brainstorm`)
- Modify: `scripts/export_questions/pipeline.py`
- Modify: `scripts/export_questions/__init__.py`

**Step 1:** Delete `extract_brainstorm` and any import; remove `"brainstorm"` key from per-lesson export dict, `stats`, and print line.

**Step 2:** If `compute_session_metrics` in `digital_teacher.py` comment references brainstorm parity, update comment.

**Step 3:** Commit.

---

### Task 3: Agents — context and prompts

**Files:**
- Modify: `agents/context_builder.py`
- Modify: `agents/diagnostic_agent.py`
- Modify: `agents/selector_agent.py`

**Step 1:** Remove `brainstorm` from `_SKILL_HINT_MAP` and `interaction in (..., "brainstorm")`; delete loop over `ic.get("brainstorm")`; remove `brainstorm_*` from `speaking_scores` in `_enrich_candidates_with_speaking`.

**Step 2:** In `diagnostic_agent`, remove brainstorm rubric lines, template vars, and `elif lms_type == "brainstorm"` (or treat legacy-only if tests need minimal handling).

**Step 3:** In `selector_agent`, remove brainstorm-specific few-shot / instructions.

**Step 4:** Commit.

---

### Task 4: min_speaking and evaluate

**Files:**
- Modify: `scripts/agent_pipeline.py`
- Modify: `web/backend/pipeline_ws.py`
- Modify: `scripts/evaluate/signal.py`
- Modify: `scripts/evaluate/report.py`
- Modify: `scripts/evaluate/preprocess_eval.py`
- Modify: `scripts/evaluate/llm_judge.py`
- Modify: `scripts/evaluate/pipeline.py`

**Step 1:** Replace reads of `overall_brainstorm_score_avg` with `overall_free_speaking_score_avg` for `min_speaking` (same tier thresholds; `None` → 100). Update `print`/log strings to say `free_speaking_avg`.

**Step 2:** In `signal.py`, rename `brainstorm_emphasis_ok` / `brainstorm_needed_speaking` to `free_speaking_emphasis_ok` / `free_speaking_needed_speaking` (or equivalent clear names) and drive thresholds from free speaking avg; update all consumers in `report.py`, `pipeline.py`, `preprocess_eval.py`, `llm_judge.py`.

**Step 3:** Remove brainstorm bullet lines from human-readable reports and LLM judge prompts; reference free speaking where weakness was described.

**Step 4:** Commit.

---

### Task 5: Backend API

**Files:**
- Modify: `web/backend/routers/lessons.py`
- Modify: `web/backend/routers/history.py`

**Step 1:** Remove `brainstorm_score_avg`, `brainstorm_attempts`, `brainstorm_questions` from response payloads (or stop including them).

**Step 2:** Commit.

---

### Task 6: Frontend

**Files:**
- Modify: `web/frontend/src/pages/LessonDetail.tsx`
- Modify: `web/frontend/src/pages/HistoryLessonDetail.tsx`
- Modify: `web/frontend/src/pages/LearningHistory.tsx`
- Modify: `web/frontend/src/pages/HomeworkResult.tsx` (types / labels only if brainstorm-specific UI exists)

**Step 1:** Remove `BrainstormSection`, brainstorm counts from totals, score cards, and list UIs; simplify types if nothing else needs `brainstorm` discriminant.

**Step 2:** Run `npm run build` (or project-equivalent) from `web/frontend`; fix TS errors.

**Step 3:** Commit.

---

### Task 7: Tests

**Files:**
- Modify: `tests/test_context_builder.py`
- Modify: `tests/test_diagnostic_agent.py`
- Modify: `tests/test_lessons_api.py`
- Grep: `brainstorm` under `tests/` and fix any remaining

**Step 1:** Update fixtures: remove brainstorm pool expectations; adjust diagnostic prompt assertions (no brainstorm stats/lines).

**Step 2:** `pytest tests/test_context_builder.py tests/test_diagnostic_agent.py tests/test_lessons_api.py -v` — expect PASS.

**Step 3:** Run full `pytest` if CI uses entire suite.

**Step 4:** Commit.

---

### Task 8: Doc hygiene (optional single line)

**Files:**
- Modify: `CLAUDE.md` or `docs/tong-hop-he-thong.md` **only if** they mention brainstorm export/pipeline explicitly (YAGNI — skip if no mention).

**Step 1:** Grep repo docs for “brainstorm” outside `docs/plans/` and update or leave per product docs policy.

**Step 2:** Final commit if changes made.

---

## Verification

- `pytest` green.
- Manual: run preprocess + export + `agent_pipeline` for one student ID; confirm `student_context["summary"]` has no `overall_brainstorm_*` and no brainstorm in `questions_export` lessons.
- Optional: hit lessons API and confirm no brainstorm keys.

---

**Plan complete and saved to `docs/plans/2026-05-05-remove-brainstorm-signal.md`.**

**Execution options:**

1. **Subagent-Driven (this session)** — fresh subagent per task, review between tasks (@ superpowers:subagent-driven-development).

2. **Parallel session (separate)** — new session with @ superpowers:executing-plans in a worktree.

**Which approach do you want?**
