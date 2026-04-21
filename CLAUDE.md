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

## Notes

- Vietnamese field names: `bai_lam` = submission, `ket_qua` = result/grade, `diem_thi` = score
- Dates in LMS files are `"YYYY-MM-DD HH:MM:SS"` (local time); MongoDB files use `$date` ISO format
- Program IDs 548–565 correspond to different curriculum units/levels
