# Homework Agent Pipeline — Design Document

**Date:** 2026-04-21  
**Student:** 2102555  
**Status:** Approved  

---

## Overview

A two-agent Python pipeline that reads existing preprocessed student data and produces a
15-question personalised homework assignment targeting weak skills and forgotten lessons.

---

## Architecture

```
student_context.json + questions_export.json
              │
              ▼
  [context_builder.py — pure Python]
    - Tier candidates by signal type
    - Filter question pool (text-only, ≥2 questions/lesson)
              │
              ├── tiered_candidates[]   (≤15, with signal_type)
              └── question_pool[]       (~200–300 questions)
              │
              ▼
  [Diagnostic Agent — GPT-4o, temperature=0.4]
    Input:  summary stats + tiered candidates + failed questions
    Output: plain English text (~600 words)
            - Skill gap analysis
            - Error clustering (recurring patterns)
            - Per-lesson priority reasoning
              │
              ▼  diagnostic_output.txt
  [Selector Agent — GPT-4o, temperature=0, structured output]
    Input:  diagnostic text + question_pool[]
    Output: JSON array of 15 homework questions
              │
              ▼
  output/homework_assignment.json
```

---

## Component Details

### 1. Context Builder (`agents/context_builder.py`)

**Candidate tiering logic:**

| Tier | Condition | Target count |
|------|-----------|-------------|
| critical | `weakness_score > 0.5` | 5–7 lessons |
| spaced_rep | `days_since > 14` AND `weakness_score ≤ 0.5` | 4–5 lessons |
| maintenance | remainder | 2–3 lessons |

**Pre-qualification filter:**
- Count usable questions per lesson: homework (non-media, has question_text) + free_speaking
- Exclude lessons with < 2 usable questions
- Exclude questions where `requires_media=true`

**Diversity-aware selection:**
- Greedy selection within each tier, sorted by `composite_priority_score` DESC
- Boost score by `0.1 × len(new_skills_not_yet_covered)` to encourage skill diversity
- Cap at 15 total candidates

**Output fields added per candidate:**
```json
{
  "signal_type": "critical | spaced_rep | maintenance",
  "usable_question_count": 12,
  "skill_coverage": ["grammar", "speaking"]
}
```

**Question pool construction:**
- Collect `lesson_id` set from selected candidates
- Flatten all usable questions from `questions_export.json` for those lessons
- Each question item: `qid`, `lesson_id`, `lesson_title`, `interaction_type`,
  `question_type`, `question_text`, `correct_answer`, `signal_type`

---

### 2. Diagnostic Agent (`agents/diagnostic_agent.py`)

**Model:** `gpt-4o`  
**Temperature:** `0.4`  
**Output format:** plain English text (no JSON, no bullet lists)

**System prompt (abridged):**
```
You are an English learning diagnostic specialist analyzing a Vietnamese student's
performance data. Before writing your analysis, identify the 3 most critical error
patterns you observe, then expand on each in clear paragraphs.
Write in English. No JSON, no bullet lists. Your output will be read by a
question selector agent as a briefing.
```

**User prompt structure:**
```
STUDENT SUMMARY:
  - Pronunciation avg: {x}/100
  - Free speaking avg: {x}/100 (breakdown of answer types)

CRITICAL LESSONS (genuinely weak):
  {lesson title} | weakness={x} | {n} days ago
  Failed questions: ...
  Worst speaking: ...

SPACED-REP LESSONS (risk of forgetting):
  ...

MAINTENANCE LESSONS:
  ...

Analyze skill gaps, recurring error patterns, and which lessons need deep
practice vs light reinforcement. Suggest what question types are most effective
per lesson.
```

**Saved to:** `output/diagnostic_output.txt`

---

### 3. Selector Agent (`agents/selector_agent.py`)

**Model:** `gpt-4o`  
**Temperature:** `0`  
**Output:** OpenAI structured output (`response_format=json_schema`)

**System prompt (abridged):**
```
You are a homework assignment designer. Select exactly 15 questions from the
provided pool. Prioritize: critical > spaced_rep > maintenance.
Ensure mix: ≥3 speaking, ≥4 grammar/fill-blank, ≥3 vocabulary.
No duplicate skill coverage from same lesson.
Tie-break: prefer fill-blank > multiple-choice > speaking when signal_type
and lesson are equal.
Return ONLY valid JSON matching the schema.
```

**Output schema per question:**
```json
{
  "question_no": 1,
  "lesson_id": 3968761,
  "lesson_title": "Unit 2C: Shopping - Lesson 5: Review 2",
  "skill_category": "grammar | vocabulary | speaking | pronunciation",
  "question_type": "Điền vào chỗ trống | free_speaking | ...",
  "question_text": "...",
  "correct_answer": "...",
  "difficulty": "easy | medium | hard",
  "reason": "Student answered 'cost' instead of 'is' — subject-verb agreement gap"
}
```

**Saved to:** `output/homework_assignment.json`

---

## File Structure

```
phase-0-learning-flow/
├── scripts/
│   ├── preprocess.py                          (existing)
│   ├── export_questions.py                    (existing)
│   └── agent_pipeline.py                      (NEW — entry point)
├── agent_pipeline.py                          (optional shim)
├── preprocess.py / export_questions.py         (optional shims)
├── agents/
│   ├── __init__.py                        (NEW)
│   ├── context_builder.py                 (NEW — tiering + filter)
│   ├── diagnostic_agent.py                (NEW — GPT-4o plain text)
│   └── selector_agent.py                  (NEW — GPT-4o structured output)
└── output/
    ├── student_context.json               (existing)
    ├── questions_export.json              (existing)
    ├── diagnostic_output.txt              (NEW — intermediate)
    └── homework_assignment.json           (NEW — final output)
```

---

## Running the Pipeline

```bash
# Prerequisites: student_context.json and questions_export.json must exist
# Set OPENAI_API_KEY in environment

export OPENAI_API_KEY=sk-...
python -m scripts.agent_pipeline

# Output:
# [1/3] Building context... 12 candidates, 247 questions in pool
# [2/3] Running diagnostic agent...
# [3/3] Running selector agent...
# Done → output/homework_assignment.json (15 questions)
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Diagnostic output = plain text | Avoids JSON parse errors; richer chain-of-thought context for selector |
| Selector uses OpenAI structured output | Guarantees valid JSON schema; temperature=0 for deterministic selection |
| Pre-filter in Python (not LLM) | Keeps LLM context small (~5–8k tokens vs 50–80k); faster and cheaper |
| Tiered candidates over naive top-N | Prevents skill concentration; ensures diversity; clearer signal to diagnostic agent |
| No framework (pure Python + openai SDK) | 2 sequential API calls don't need orchestration abstractions; easier to debug |
| English for diagnostic output | GPT-4o reasons better in English; selector agent reads it as internal briefing |
