"""
Selector agent — GPT-4o, structured JSON output.

Input:  diagnostic_text (str) + question_pool (list of question dicts)
Output: list of 15 homework question dicts

Uses OpenAI structured output (response_format json_schema) for guaranteed
valid JSON. temperature=0 for deterministic selection.

Note: Uses chat.completions.create with json_schema response_format (not
chat.completions.parse), which expects a Pydantic model class.
"""

from __future__ import annotations

import json
import os

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
                        "question_no",
                        "lesson_id",
                        "lesson_title",
                        "skill_category",
                        "question_type",
                        "question_text",
                        "correct_answer",
                        "difficulty",
                        "reason",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "question_no": {"type": "integer"},
                        "lesson_id": {"type": "integer"},
                        "lesson_title": {"type": "string"},
                        "skill_category": {
                            "type": "string",
                            "enum": ["grammar", "vocabulary", "speaking", "pronunciation", "other"],
                        },
                        "question_type": {"type": "string"},
                        "question_text": {"type": "string"},
                        "correct_answer": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "reason": {"type": "string"},
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
            f'lesson_title="{q.get("lesson_title", "")}" '
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


def parse_response(raw: str | None) -> list:
    if not raw:
        raise ValueError("Empty response from model")
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

    response = client.chat.completions.create(
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
