# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a data directory containing JSON exports from an English learning platform (rinoedu.ai / VH Digital Teacher) for student ID **2102555**. All files relate to a single student's learning activity across "Phase 0" English lessons (Vietnamese curriculum, levels 1–5).

## Data Files

### Program/Lesson Curriculum
- `programe_lesson_548.json`, `program_lesson_549–565.json` — Curriculum structure per program ID. Each file contains an array of lessons with nested `tutor_program_lesson_sections` that link to LMS content (`lms_id`, `lms_link`, `link_practice`).
  - Section types: `10` = video/content, `4` = practice exercise
  - `is_required: 1` marks mandatory sections; `lms_num_question` gives question count

### Student Practice Results
- `lms_practice_result_2102555.csv.json` — One record per practice attempt. Key fields: `practice_id`, `diem_thi` (score 0–1), `total_correct_question`, `total_question`, `create_date`.
- `lms_practice_result_detail_2102555_2.json` — Per-question detail rows linked via `result_id`. `bai_lam` = student's raw answer (JSON string), `ket_qua` = graded answer with `r` (correct bool) and `p` (point) per option. `is_correct: 1` = question answered correctly.

### Tutor Lesson List
- `tutor_lessons_2102555.json` — Flat list of lessons with LMS practice IDs and completion counts (`completed_lesson`). Each lesson appears twice: once for "Bài tập" (exercises) and once for "Luyện tập" (practice), with different `lms_id`s.

### Digital Teacher Session Data (MongoDB exports)
- `vh_digital_teacher.learning_sessions_2102555_1.json` — Session-level records with flow/section completion checkpoints. `erpLessonId` links to ERP lesson IDs; `status` can be `COMPLETED`.
- `vh_digital_teacher.learning_results_2102555_1.json` — Individual interaction results within sessions. `lmsType` is `practice`; `interactionType` is `AUDIO` for speaking tasks. Contains `userTranscript`, `audioUrl`, and `score`.

## Key Relationships

```
program_lesson_{id}.json
  └── lesson.id → tutor_lessons (id field)
                → vh_digital_teacher.learning_sessions (erpLessonId)
  └── section.lms_id → lms_practice_result (practice_id)
                     → lms_practice_result_detail (practice_id)

lms_practice_result.id → lms_practice_result_detail.result_id
vh_digital_teacher.learning_sessions._id → learning_results.sessionId
```

## Homework agent pipeline (code)

After raw exports exist under `data/`, run preprocessing and optional question export, then the two-agent homework pipeline.

Implementation lives under `scripts/` as **Python packages** (split from former monolithic modules):

- **`scripts/preprocess/`** — `config.py`, `loaders.py`, `lms_questions.py`, `digital_teacher.py`, `pipeline.py`, … Entry: `python -m scripts.preprocess`. Mutable paths live on **`scripts.preprocess.config`** (`DATA_DIR`, `STUDENT_ID`, `OUTPUT_FILE`).
- **`scripts/export_questions/`** — `bank.py`, `homework.py`, `in_class.py`, `pipeline.py`, … Entry: `python -m scripts.export_questions`. Before loading tutor/LMS files it sets **`preprocess.config.DATA_DIR`** to match this run.
- **`scripts/evaluate/`** — metrics + LLM judge + reports; entry: `python -m scripts.evaluate`.
- **Single-file utilities:** `scripts/agent_pipeline.py`, `scripts/lms_question_rich.py`, `scripts/analyze_pipeline_model_outputs.py`.

From the repo root, prefer **`python -m scripts.<package>`**; thin shims at the repo root (`preprocess.py`, `export_questions.py`, `evaluate.py`, …) call the same code for backward compatibility.

| Step | Command | Output |
|------|---------|--------|
| Preprocess | `python -m scripts.preprocess [student_id]` or `python preprocess.py [student_id]` | `output/<student_id>/student_context.json` (scored candidates + summary) |
| Question export | `python -m scripts.export_questions [student_id]` or `python export_questions.py [student_id]` | `output/<student_id>/questions_export.json` |
| Homework agents | `OPENAI_API_KEY` and/or `GOOGLE_API_KEY`; `python -m scripts.agent_pipeline [student_id] --model <id>` (or `python agent_pipeline.py …`) | under `output/<student_id>/`: `homework_assignment.json`, `homework_by_model.json`, v.v. (15 questions per run; một bản mới nhất mỗi model) |
| Evaluate (optional) | `python -m scripts.evaluate <student_id>` or `python evaluate.py …` | `output/<student_id>/evaluation_report.json` (+ `.md`) |

- **Dependencies:** `pip install -r requirements.txt` (see `agents/` for context builder, diagnostic, selector modules; tests in `tests/`).
- **Design:** `docs/plans/2026-04-21-homework-agent-design.md` and `docs/plans/2026-04-21-homework-agent-pipeline.md`.
- **Vietnamese system overview (flow, components):** `docs/tong-hop-he-thong.md`.

## Notes

- Vietnamese field names: `bai_lam` = submission, `ket_qua` = result/grade, `diem_thi` = score
- Dates in LMS files are `"YYYY-MM-DD HH:MM:SS"` (local time); MongoDB files use `$date` ISO format
- Program IDs 548–565 correspond to different curriculum units/levels
