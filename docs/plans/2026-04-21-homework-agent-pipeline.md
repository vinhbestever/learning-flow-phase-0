# Homework Agent Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a two-agent Python pipeline that reads `output/student_context.json` + `output/questions_export.json` and writes `output/homework_assignment.json` containing 15 personalised homework questions.

**Architecture:** A pure-Python pre-filter tiers candidates by urgency (critical/spaced_rep/maintenance) and builds a text-renderable question pool. Diagnostic agent (GPT-4o, plain text) analyses skill gaps and error patterns. Selector agent (GPT-4o, structured output) picks 15 questions from the pool guided by the diagnostic text.

**Tech Stack:** Python 3.10+, `openai` SDK (`pip install openai`), no frameworks. `OPENAI_API_KEY` env var required at runtime.

---

## Task 1: Project scaffold

**Files:**
- Create: `agents/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_context_builder.py` (empty for now)

**Step 1: Create package directories**

```bash
mkdir -p agents tests
touch agents/__init__.py tests/__init__.py
```

**Step 2: Install openai SDK**

```bash
pip install openai
python -c "import openai; print(openai.__version__)"
```
Expected: version string printed (≥1.30).

**Step 3: Commit scaffold**

```bash
git add agents/ tests/
git commit -m "feat: scaffold agents package and tests dir"
```

---

## Task 2: Context builder — candidate tiering

**Files:**
- Create: `agents/context_builder.py`
- Test: `tests/test_context_builder.py`

### What this module does

Reads `scored_candidates` from `student_context.json` and questions from
`questions_export.json`. Returns two things:
1. `tiered_candidates` — up to 15 lessons enriched with `signal_type` and `usable_question_count`
2. `question_pool` — flat list of text-renderable questions from those lessons

### Step 1: Write failing tests

```python
# tests/test_context_builder.py
import json, pytest
from agents.context_builder import tier_candidates, build_question_pool, build_context

CANDIDATE_CRITICAL = {
    "lesson_id": 1, "title": "Lesson A", "level": 5,
    "days_since_last_practice": 20, "forgetting_score": 1.0,
    "weakness_score": 0.6, "composite_priority_score": 0.8,
    "weak_skills": ["grammar"], "failed_text_questions": [],
    "worst_speaking_items": [], "practice_ids": {"bai_tap": None, "luyen_tap": 101},
}
CANDIDATE_SPACED = {
    **CANDIDATE_CRITICAL,
    "lesson_id": 2, "title": "Lesson B",
    "weakness_score": 0.3, "composite_priority_score": 0.65,
    "days_since_last_practice": 16,
}
CANDIDATE_MAINTENANCE = {
    **CANDIDATE_CRITICAL,
    "lesson_id": 3, "title": "Lesson C",
    "weakness_score": 0.2, "composite_priority_score": 0.4,
    "days_since_last_practice": 10,
}

QUESTIONS_EXPORT = {
    "lessons": [
        {
            "lesson_id": 1,
            "title": "Lesson A",
            "in_class": {
                "free_speaking": [
                    {"interaction_type": "free_speaking", "question": "What do you eat?",
                     "question_type": "speaking_unscripted"}
                ]
            },
            "homework": {
                "bai_tap": None,
                "luyen_tap": {
                    "practice_id": 101, "score": 0.8, "correct": 8, "total": 10,
                    "questions": [
                        {"question_id": 1001, "question_folder": "Grammar",
                         "question_type": "Điền vào chỗ trống",
                         "question_text": "She ___ a cat.", "requires_media": False,
                         "correct_answer": "has"},
                        {"question_id": 1002, "question_folder": "Grammar",
                         "question_type": "Một lựa chọn",
                         "question_text": None, "requires_media": True,
                         "correct_answer": "blue"},  # media — should be excluded
                    ]
                }
            }
        },
        {
            "lesson_id": 2,
            "title": "Lesson B",
            "in_class": {"free_speaking": []},
            "homework": {
                "bai_tap": {
                    "practice_id": 201, "score": 0.9, "correct": 9, "total": 10,
                    "questions": [
                        {"question_id": 2001, "question_folder": "Vocabulary",
                         "question_type": "Điền vào chỗ trống",
                         "question_text": "A dog is an ___.", "requires_media": False,
                         "correct_answer": "animal"},
                    ]
                },
                "luyen_tap": None,
            }
        },
        {
            "lesson_id": 3, "title": "Lesson C",
            "in_class": {"free_speaking": []},
            "homework": {"bai_tap": None, "luyen_tap": None}
            # zero usable questions — should be excluded
        }
    ]
}


def test_tier_candidates_labels():
    candidates = [CANDIDATE_CRITICAL, CANDIDATE_SPACED, CANDIDATE_MAINTENANCE]
    tiered = tier_candidates(candidates)
    by_id = {c["lesson_id"]: c for c in tiered}
    assert by_id[1]["signal_type"] == "critical"
    assert by_id[2]["signal_type"] == "spaced_rep"
    assert by_id[3]["signal_type"] == "maintenance"


def test_tier_candidates_excludes_zero_question_lessons():
    candidates = [CANDIDATE_CRITICAL, CANDIDATE_MAINTENANCE]
    tiered = tier_candidates(candidates, questions_export=QUESTIONS_EXPORT, min_questions=2)
    ids = [c["lesson_id"] for c in tiered]
    # lesson 3 has 0 usable questions — excluded
    assert 3 not in ids
    assert 1 in ids


def test_tier_candidates_caps_at_15():
    many = [
        {**CANDIDATE_CRITICAL, "lesson_id": i, "composite_priority_score": 0.9 - i * 0.01}
        for i in range(1, 25)
    ]
    tiered = tier_candidates(many)
    assert len(tiered) <= 15


def test_build_question_pool_excludes_media():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    qtypes = [q["question_type"] for q in pool]
    # question_id 1002 has requires_media=True — must not appear
    assert all(q.get("requires_media") is False for q in pool)
    # question_id 1001 should be present
    assert any(q["question_id"] == 1001 for q in pool)


def test_build_question_pool_includes_free_speaking():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    assert any(q["interaction_type"] == "free_speaking" for q in pool)


def test_build_question_pool_attaches_lesson_metadata():
    lesson_ids = {1}
    pool = build_question_pool(lesson_ids, QUESTIONS_EXPORT)
    for q in pool:
        assert "lesson_id" in q
        assert "lesson_title" in q
        assert "signal_type" in q
```

**Step 2: Run tests — verify they all fail**

```bash
python -m pytest tests/test_context_builder.py -v
```
Expected: 6 errors (ImportError — module not yet created).

**Step 3: Implement `agents/context_builder.py`**

```python
"""
Pre-filter and tier scored_candidates before sending to LLM agents.

Tiering rules:
  critical    weakness_score > 0.5
  spaced_rep  days_since > 14 AND weakness_score <= 0.5
  maintenance everything else

Selection: greedy within each tier, sorted by composite_priority_score DESC.
Skill-diversity boost: +0.1 per new skill category not yet covered.
Cap: MAX_CANDIDATES total across all tiers.
"""

import json

MAX_CANDIDATES = 15
MIN_QUESTIONS = 2  # lessons with fewer usable questions are excluded


def _count_usable(lesson: dict) -> tuple[int, list]:
    """Return (count, list) of text-renderable questions for a lesson."""
    usable = []
    hw = lesson.get("homework") or {}
    for ptype in ("bai_tap", "luyen_tap"):
        practice = hw.get(ptype) or {}
        for q in practice.get("questions") or []:
            if not q.get("requires_media") and q.get("question_text"):
                usable.append({**q, "source": ptype})
    for item in (lesson.get("in_class") or {}).get("free_speaking") or []:
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
    q_map = {}
    if questions_export:
        q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}

    def _signal(c):
        if c.get("weakness_score", 0) > 0.5:
            return "critical"
        if (c.get("days_since_last_practice") or 0) > 14:
            return "spaced_rep"
        return "maintenance"

    enriched = []
    for c in candidates:
        signal = _signal(c)
        lesson = q_map.get(c["lesson_id"], {})
        count, _ = _count_usable(lesson)
        if questions_export and count < min_questions:
            continue
        enriched.append({
            **c,
            "signal_type": signal,
            "usable_question_count": count,
        })

    tier_order = ["critical", "spaced_rep", "maintenance"]
    selected = []
    covered_skills = set()

    for tier in tier_order:
        tier_items = [c for c in enriched if c["signal_type"] == tier]
        for c in tier_items:
            new_skills = set(c.get("weak_skills") or []) - covered_skills
            c["_adjusted"] = c["composite_priority_score"] + 0.1 * len(new_skills)
        tier_items.sort(key=lambda c: c["_adjusted"], reverse=True)
        for c in tier_items:
            if len(selected) >= max_candidates:
                break
            selected.append(c)
            covered_skills.update(c.get("weak_skills") or [])

    # Clean up internal field
    for c in selected:
        c.pop("_adjusted", None)

    return selected


def build_question_pool(lesson_ids: set, questions_export: dict) -> list:
    """
    Flatten usable questions from the given lesson_ids.
    Attaches lesson_id, lesson_title, signal_type (from tiered_candidates if available).
    """
    q_map = {l["lesson_id"]: l for l in questions_export.get("lessons", [])}
    pool = []
    for lid in lesson_ids:
        lesson = q_map.get(lid, {})
        _, usable = _count_usable(lesson)
        title = lesson.get("title", "")
        for q in usable:
            pool.append({
                "lesson_id": lid,
                "lesson_title": title,
                "signal_type": None,  # caller sets this after tier_candidates
                **q,
            })
    return pool


def build_context(
    student_context: dict,
    questions_export: dict,
    max_candidates: int = MAX_CANDIDATES,
) -> tuple[list, list]:
    """
    Main entry: returns (tiered_candidates, question_pool).
    tiered_candidates: enriched candidate list with signal_type
    question_pool: flat list of usable questions from those lessons
    """
    raw_candidates = student_context.get("scored_candidates", [])
    tiered = tier_candidates(raw_candidates, questions_export, max_candidates=max_candidates)

    signal_map = {c["lesson_id"]: c["signal_type"] for c in tiered}
    lesson_ids = set(signal_map.keys())
    pool = build_question_pool(lesson_ids, questions_export)
    for q in pool:
        q["signal_type"] = signal_map.get(q["lesson_id"])

    return tiered, pool
```

**Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_context_builder.py -v
```
Expected: 6 PASSED.

**Step 5: Commit**

```bash
git add agents/context_builder.py tests/test_context_builder.py
git commit -m "feat: context builder — tier candidates and build question pool"
```

---

## Task 3: Diagnostic agent

**Files:**
- Create: `agents/diagnostic_agent.py`
- Create: `tests/test_diagnostic_agent.py`

### What this module does

Builds the prompt from `tiered_candidates` + `summary`, calls GPT-4o,
returns the plain-text diagnostic string. Also saves it to a file path if given.

### Step 1: Write failing tests

```python
# tests/test_diagnostic_agent.py
import pytest
from unittest.mock import patch, MagicMock
from agents.diagnostic_agent import build_prompt, run_diagnostic

SUMMARY = {
    "overall_pronunciation_score_avg": 86.96,
    "overall_free_speaking_score_avg": 30.71,
    "overall_free_speaking_answer_type_dist": {"correct": 48, "incorrect": 34, "inaccordant": 16},
    "total_lessons": 50,
    "lessons_by_status": {"completed": 48, "in_class_only": 2},
}

CANDIDATES = [
    {
        "lesson_id": 1, "title": "Lesson A", "signal_type": "critical",
        "days_since_last_practice": 20, "weakness_score": 0.79,
        "composite_priority_score": 0.89, "weak_skills": ["grammar"],
        "failed_text_questions": [
            {"question_text": "She ___ a cat.", "correct_answer": "has",
             "student_answer": "have", "question_type": "Điền vào chỗ trống"}
        ],
        "worst_speaking_items": [
            {"question": "What do you eat?", "user_transcript": "I eat bitter.",
             "score": 0, "answer_type": "inaccordant"}
        ],
        "usable_question_count": 8,
    },
    {
        "lesson_id": 2, "title": "Lesson B", "signal_type": "spaced_rep",
        "days_since_last_practice": 18, "weakness_score": 0.3,
        "composite_priority_score": 0.65, "weak_skills": [],
        "failed_text_questions": [], "worst_speaking_items": [],
        "usable_question_count": 5,
    }
]


def test_build_prompt_contains_summary_stats():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "86.96" in prompt
    assert "30.71" in prompt


def test_build_prompt_contains_lesson_titles():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "Lesson A" in prompt
    assert "Lesson B" in prompt


def test_build_prompt_labels_signal_types():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "CRITICAL" in prompt.upper() or "critical" in prompt
    assert "SPACED" in prompt.upper() or "spaced_rep" in prompt


def test_build_prompt_includes_failed_question():
    prompt = build_prompt(SUMMARY, CANDIDATES)
    assert "She ___ a cat." in prompt


def test_run_diagnostic_returns_string():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Student has weak grammar."))]
    )
    result = run_diagnostic(SUMMARY, CANDIDATES, client=mock_client)
    assert isinstance(result, str)
    assert len(result) > 0


def test_run_diagnostic_calls_gpt4o():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Analysis text."))]
    )
    run_diagnostic(SUMMARY, CANDIDATES, client=mock_client)
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["temperature"] == 0.4
```

**Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_diagnostic_agent.py -v
```
Expected: ImportError on all 6 tests.

**Step 3: Implement `agents/diagnostic_agent.py`**

```python
"""
Diagnostic agent — GPT-4o, plain text output.

Input:  summary dict + tiered_candidates list
Output: plain English analysis string (~500-700 words)

The output is intentionally NOT structured JSON. It serves as a rich
chain-of-thought briefing for the selector agent.
"""

from __future__ import annotations
import os
from openai import OpenAI

SYSTEM_PROMPT = """\
You are an English learning diagnostic specialist analyzing a Vietnamese student's \
performance data. The student is in Phase 0, levels 4–5.

Before writing your analysis, identify the 3 most critical error patterns you \
observe, then expand on each in clear paragraphs. Write in English. \
No JSON, no bullet lists, no markdown headers. \
Your output will be read by a question selector agent as a briefing document.\
"""

USER_TEMPLATE = """\
STUDENT SUMMARY
---------------
Lessons completed: {completed}/{total}
Pronunciation avg: {pron}/100
Free speaking avg: {free}/100
Free speaking answer distribution: {answer_dist}

LESSONS TO REVIEW
-----------------
{lesson_blocks}

Analyze: identify skill gaps, recurring error patterns across lessons, which \
lessons need deep practice vs light reinforcement, and what question types \
are most effective per lesson.\
"""

LESSON_BLOCK_TEMPLATE = """\
[{signal_type_upper}] "{title}" | weakness={weakness:.2f} | {days}d ago | {q_count} usable questions
  Weak skills: {skills}
  Failed questions: {failed_q}
  Worst speaking: {worst_sp}\
"""


def _fmt_failed_q(questions: list) -> str:
    if not questions:
        return "none"
    parts = []
    for q in questions[:3]:
        parts.append(
            f'"{q.get("question_text", "")[:80]}" '
            f'(correct: {q.get("correct_answer")}, '
            f'student: {q.get("student_answer")})'
        )
    return " | ".join(parts)


def _fmt_speaking(items: list) -> str:
    if not items:
        return "none"
    parts = []
    for s in items[:2]:
        parts.append(
            f'Q: "{s.get("question", "")}" → '
            f'"{s.get("user_transcript", "")}" [{s.get("answer_type")}]'
        )
    return " | ".join(parts)


def build_prompt(summary: dict, candidates: list) -> str:
    by_status = summary.get("lessons_by_status", {})
    completed = by_status.get("completed", 0)
    total = summary.get("total_lessons", 0)

    lesson_blocks = []
    for c in candidates:
        block = LESSON_BLOCK_TEMPLATE.format(
            signal_type_upper=c.get("signal_type", "").upper(),
            title=c.get("title", ""),
            weakness=c.get("weakness_score", 0),
            days=c.get("days_since_last_practice", 0),
            q_count=c.get("usable_question_count", 0),
            skills=", ".join(c.get("weak_skills") or []) or "none identified",
            failed_q=_fmt_failed_q(c.get("failed_text_questions") or []),
            worst_sp=_fmt_speaking(c.get("worst_speaking_items") or []),
        )
        lesson_blocks.append(block)

    return USER_TEMPLATE.format(
        completed=completed,
        total=total,
        pron=summary.get("overall_pronunciation_score_avg", "N/A"),
        free=summary.get("overall_free_speaking_score_avg", "N/A"),
        answer_dist=summary.get("overall_free_speaking_answer_type_dist", {}),
        lesson_blocks="\n\n".join(lesson_blocks),
    )


def run_diagnostic(
    summary: dict,
    candidates: list,
    client: OpenAI | None = None,
    save_path: str | None = None,
) -> str:
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = build_prompt(summary, candidates)

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

    return text
```

**Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_diagnostic_agent.py -v
```
Expected: 6 PASSED.

**Step 5: Commit**

```bash
git add agents/diagnostic_agent.py tests/test_diagnostic_agent.py
git commit -m "feat: diagnostic agent — GPT-4o plain text analysis"
```

---

## Task 4: Selector agent

**Files:**
- Create: `agents/selector_agent.py`
- Create: `tests/test_selector_agent.py`

### What this module does

Takes `diagnostic_text` + `question_pool`, calls GPT-4o with `response_format=json_schema`
to get a structured list of exactly 15 homework questions. Returns parsed dict.

### Step 1: Write failing tests

```python
# tests/test_selector_agent.py
import json, pytest
from unittest.mock import patch, MagicMock
from agents.selector_agent import build_prompt, parse_response, HOMEWORK_SCHEMA, run_selector

DIAGNOSTIC_TEXT = "Student shows weak grammar. Struggles with subject-verb agreement."

QUESTION_POOL = [
    {
        "lesson_id": 1, "lesson_title": "Lesson A", "signal_type": "critical",
        "question_id": 1001, "question_folder": "Grammar",
        "question_type": "Điền vào chỗ trống",
        "question_text": "She ___ a cat.", "requires_media": False,
        "correct_answer": "has", "interaction_type": None,
    },
    {
        "lesson_id": 1, "lesson_title": "Lesson A", "signal_type": "critical",
        "question_id": None, "question_folder": "Speaking",
        "question_type": "free_speaking",
        "question_text": "What do you eat?", "requires_media": False,
        "correct_answer": None, "interaction_type": "free_speaking",
    },
]

VALID_HOMEWORK_ITEM = {
    "question_no": 1,
    "lesson_id": 1,
    "lesson_title": "Lesson A",
    "skill_category": "grammar",
    "question_type": "Điền vào chỗ trống",
    "question_text": "She ___ a cat.",
    "correct_answer": "has",
    "difficulty": "medium",
    "reason": "Student failed subject-verb agreement",
}


def test_build_prompt_contains_diagnostic_text():
    prompt = build_prompt(DIAGNOSTIC_TEXT, QUESTION_POOL)
    assert "subject-verb agreement" in prompt


def test_build_prompt_contains_question_pool():
    prompt = build_prompt(DIAGNOSTIC_TEXT, QUESTION_POOL)
    assert "She ___ a cat." in prompt
    assert "What do you eat?" in prompt


def test_homework_schema_has_required_fields():
    props = HOMEWORK_SCHEMA["schema"]["properties"]["homework"]["items"]["properties"]
    for field in ("question_no", "lesson_id", "skill_category", "question_text",
                  "correct_answer", "difficulty", "reason"):
        assert field in props, f"Missing field: {field}"


def test_parse_response_returns_list():
    raw = json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 15})
    result = parse_response(raw)
    assert isinstance(result, list)
    assert len(result) == 15


def test_parse_response_validates_count():
    raw = json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 10})
    with pytest.raises(ValueError, match="Expected 15"):
        parse_response(raw)


def test_run_selector_calls_structured_output():
    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(
            content=json.dumps({"homework": [VALID_HOMEWORK_ITEM] * 15})
        ))]
    )
    result = run_selector(DIAGNOSTIC_TEXT, QUESTION_POOL, client=mock_client)
    assert len(result) == 15
    call_kwargs = mock_client.chat.completions.parse.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["temperature"] == 0
```

**Step 2: Run tests — verify they fail**

```bash
python -m pytest tests/test_selector_agent.py -v
```
Expected: ImportError on all 6 tests.

**Step 3: Implement `agents/selector_agent.py`**

```python
"""
Selector agent — GPT-4o, structured JSON output.

Input:  diagnostic_text (str) + question_pool (list of question dicts)
Output: list of 15 homework question dicts

Uses OpenAI structured output (response_format json_schema) for guaranteed
valid JSON. temperature=0 for deterministic selection.
"""

from __future__ import annotations
import json, os
from openai import OpenAI

HOMEWORK_SCHEMA = {
    "name": "homework_assignment",
    "strict": True,
    "schema": {
        "type": "object",
        "required": ["homework"],
        "additionalProperties": False,
        "properties": {
            "homework": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "question_no", "lesson_id", "lesson_title",
                        "skill_category", "question_type", "question_text",
                        "correct_answer", "difficulty", "reason",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "question_no":    {"type": "integer"},
                        "lesson_id":      {"type": "integer"},
                        "lesson_title":   {"type": "string"},
                        "skill_category": {"type": "string", "enum": ["grammar", "vocabulary", "speaking", "pronunciation", "other"]},
                        "question_type":  {"type": "string"},
                        "question_text":  {"type": "string"},
                        "correct_answer": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "difficulty":     {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "reason":         {"type": "string"},
                    },
                },
            }
        },
    },
}

SYSTEM_PROMPT = """\
You are a homework assignment designer for a Vietnamese student learning English (Phase 0, levels 4–5).
Select exactly 15 questions from the provided pool to create a balanced, targeted homework set.
Rules:
- Prioritise: critical signal > spaced_rep > maintenance
- Include at least: 3 speaking, 4 grammar or fill-blank, 3 vocabulary
- No duplicate skill coverage from the same lesson
- Tie-break: prefer fill-blank > multiple-choice > speaking when signal_type and lesson are equal
Return ONLY valid JSON matching the schema. No markdown, no explanation.\
"""

USER_TEMPLATE = """\
DIAGNOSTIC ANALYSIS
-------------------
{diagnostic_text}

QUESTION POOL ({count} questions available)
--------------------------------------------
{pool_text}

Select exactly 15 questions. Assign question_no 1–15 in order of priority.\
"""


def _pool_to_text(pool: list) -> str:
    lines = []
    for i, q in enumerate(pool):
        qid = q.get("question_id") or f"fs-{i}"
        lines.append(
            f'[{q.get("signal_type", "?")}] qid={qid} lesson_id={q["lesson_id"]} '
            f'type="{q["question_type"]}" '
            f'text="{(q.get("question_text") or "")[:120]}" '
            f'answer="{q.get("correct_answer") or "open"}"'
        )
    return "\n".join(lines)


def build_prompt(diagnostic_text: str, question_pool: list) -> str:
    return USER_TEMPLATE.format(
        diagnostic_text=diagnostic_text,
        count=len(question_pool),
        pool_text=_pool_to_text(question_pool),
    )


def parse_response(raw: str) -> list:
    data = json.loads(raw)
    homework = data.get("homework", [])
    if len(homework) != 15:
        raise ValueError(f"Expected 15 questions, got {len(homework)}")
    return homework


def run_selector(
    diagnostic_text: str,
    question_pool: list,
    client: OpenAI | None = None,
    save_path: str | None = None,
) -> list:
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = build_prompt(diagnostic_text, question_pool)

    response = client.chat.completions.parse(
        model="gpt-4o",
        temperature=0,
        response_format={"type": "json_schema", "json_schema": HOMEWORK_SCHEMA},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content
    homework = parse_response(raw)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework
```

**Step 4: Run tests — verify they pass**

```bash
python -m pytest tests/test_selector_agent.py -v
```
Expected: 6 PASSED.

**Step 5: Commit**

```bash
git add agents/selector_agent.py tests/test_selector_agent.py
git commit -m "feat: selector agent — GPT-4o structured output for 15 homework questions"
```

---

## Task 5: Pipeline entry point

**Files:**
- Create: `scripts/agent_pipeline.py` (thin `agent_pipeline.py` at repo root delegates here)

### What this module does

Orchestrates the full pipeline: load JSON files → build_context → run_diagnostic →
run_selector → save output. Prints progress to stdout.

**Step 1: Implement `agent_pipeline.py`**

```python
"""
Entry point for the homework agent pipeline.

Usage:
    export OPENAI_API_KEY=sk-...
    python -m scripts.agent_pipeline

Prerequisites:
    output/<student_id>/student_context.json   (run scripts.preprocess first)
    output/<student_id>/questions_export.json  (run scripts.export_questions first)

Outputs:
    output/diagnostic_output.txt
    output/homework_assignment.json
"""

import json, os, sys
from pathlib import Path

STUDENT_CONTEXT_PATH  = "output/student_context.json"
QUESTIONS_EXPORT_PATH = "output/questions_export.json"
DIAGNOSTIC_OUTPUT     = "output/diagnostic_output.txt"
HOMEWORK_OUTPUT       = "output/homework_assignment.json"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # Validate prerequisites
    for path in (STUDENT_CONTEXT_PATH, QUESTIONS_EXPORT_PATH):
        if not Path(path).exists():
            print(f"ERROR: {path} not found. Run preprocess.py / export_questions.py first.")
            sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    print("Loading data files...")
    student_context  = load_json(STUDENT_CONTEXT_PATH)
    questions_export = load_json(QUESTIONS_EXPORT_PATH)

    # Step 1: Build context
    from agents.context_builder import build_context
    print("[1/3] Building context (tiering candidates, building question pool)...")
    tiered_candidates, question_pool = build_context(student_context, questions_export)
    print(f"      {len(tiered_candidates)} candidates | {len(question_pool)} questions in pool")
    tier_counts = {}
    for c in tiered_candidates:
        t = c["signal_type"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"      Tiers: {tier_counts}")

    # Step 2: Diagnostic agent
    from agents.diagnostic_agent import run_diagnostic
    print("[2/3] Running diagnostic agent (GPT-4o)...")
    diagnostic_text = run_diagnostic(
        summary=student_context["summary"],
        candidates=tiered_candidates,
        save_path=DIAGNOSTIC_OUTPUT,
    )
    print(f"      Diagnostic saved → {DIAGNOSTIC_OUTPUT} ({len(diagnostic_text)} chars)")

    # Step 3: Selector agent
    from agents.selector_agent import run_selector
    print("[3/3] Running selector agent (GPT-4o structured output)...")
    homework = run_selector(
        diagnostic_text=diagnostic_text,
        question_pool=question_pool,
        save_path=HOMEWORK_OUTPUT,
    )
    print(f"      Done → {HOMEWORK_OUTPUT} ({len(homework)} questions)")

    # Summary
    print("\n--- Homework Assignment Summary ---")
    for q in homework:
        print(
            f"  {q['question_no']:>2}. [{q['skill_category']:<12}] [{q['difficulty']:<6}] "
            f"{q['question_text'][:60]}"
        )


if __name__ == "__main__":
    main()
```

**Step 2: Dry-run (no API key needed — just test imports and data loading)**

```bash
python -c "
import json
from agents.context_builder import build_context
ctx = json.load(open('output/student_context.json'))
qex = json.load(open('output/questions_export.json'))
candidates, pool = build_context(ctx, qex)
print(f'Candidates: {len(candidates)}, Pool: {len(pool)}')
for c in candidates[:3]:
    print(f'  [{c[\"signal_type\"]}] {c[\"title\"][:50]} | usable_q={c[\"usable_question_count\"]}')
"
```
Expected: prints candidate counts and tier labels, no errors.

**Step 3: Run full pipeline (requires OPENAI_API_KEY)**

```bash
export OPENAI_API_KEY=sk-...
python -m scripts.agent_pipeline
```
Expected:
```
[1/3] Building context... 12 candidates | 230 questions in pool
      Tiers: {'critical': 5, 'spaced_rep': 5, 'maintenance': 2}
[2/3] Running diagnostic agent (GPT-4o)...
      Diagnostic saved → output/diagnostic_output.txt (650 chars)
[3/3] Running selector agent (GPT-4o structured output)...
      Done → output/homework_assignment.json (15 questions)
--- Homework Assignment Summary ---
   1. [grammar     ] [medium] She ___ a cat.
   ...
```

**Step 4: Verify output**

```bash
python -c "
import json
hw = json.load(open('output/homework_assignment.json'))
assert len(hw['homework']) == 15, 'Must have exactly 15 questions'
skill_cats = [q['skill_category'] for q in hw['homework']]
print('Skill distribution:', {s: skill_cats.count(s) for s in set(skill_cats)})
print('Difficulties:', {d: [q['difficulty'] for q in hw['homework']].count(d) for d in ['easy','medium','hard']})
print('OK')
"
```
Expected: prints distributions, `OK`.

**Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: All tests PASSED.

**Step 6: Commit**

```bash
git add scripts/agent_pipeline.py agent_pipeline.py
git commit -m "feat: agent pipeline entry point — orchestrates context→diagnostic→selector"
```

---

## Task 6: Run full test suite and final check

**Step 1: Run all tests**

```bash
python -m pytest tests/ -v --tb=short
```
Expected: All PASSED, 0 failures.

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete homework agent pipeline (context builder + diagnostic + selector)"
```
