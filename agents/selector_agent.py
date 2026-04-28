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

import html
import json
import os

from openai import OpenAI

from agents.model_config import (
    DEFAULT_HOMEWORK_MODEL,
    openai_responses_include_temperature,
    openai_uses_responses_api,
)

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
                        "question_id",
                        "requires_media",
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
                        "question_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        "requires_media": {"type": "boolean"},
                    },
                },
            }
        },
    },
}

SYSTEM_PROMPT = """\
You are a homework assignment designer for a Vietnamese student learning English (Phase 0, levels 4–5).
Select exactly 15 questions from the provided pool to create a balanced, targeted homework set.

SELECTION RULES:
- Prioritise: critical signal > spaced_rep > maintenance
- Include at least: 3 speaking, 4 grammar or fill-blank, 3 vocabulary
- Per-lesson cap: pick at most 2 questions from any single lesson. If two questions come from \
the same lesson, they MUST have different skill_hint values (e.g. one grammar + one speaking).
- Tie-break: prefer fill-blank > multiple-choice > speaking when signal_type and lesson are equal
- MEDIA: pool lines tagged MEDIA=yes need image/audio on LMS. Include 2–4 such questions if the \
pool offers them; set requires_media=true and copy the same question_id as in the pool. For \
non-media lines set requires_media=false. For free-speaking pool rows (no question_id) use \
question_id=null and requires_media=false.
- Use the skill_hint field on each pool line to guide skill_category assignment; \
map "other" to whichever of grammar/vocabulary/speaking best fits the question_text.

REASON FIELD RULES — this is the most important field:
Write 1–2 sentences per question IN VIETNAMESE that are specific to THIS student's actual performance.
Always reference at least one of: a specific wrong answer they gave, a speaking transcript \
(e.g. "học sinh nói 'It's black' thay vì 'It's blue'"), a speaking score from speaking_scores \
(e.g. "brainstorm=0/100"), a forgetting duration, or a named error pattern from the diagnostic.
Do NOT write generic labels like "critical signal, grammar practice".
The reason field MUST be written entirely in Vietnamese.

Good reason examples (in Vietnamese):
- "Học sinh điền 'cost' thay vì 'is' trong bài fill-blank này — lỗi chia động từ theo chủ ngữ xuất hiện ở 3 bài học khác nhau theo kết quả chẩn đoán. Bài đã học cách đây 20 ngày (đã quên hoàn toàn)."
- "Điểm brainstorm 0/100 trong bài này: học sinh nói 'Can see a bus stop, a train station' khi được yêu cầu liệt kê 4 targets — thiếu 'bus' và 'train' dù đã thấy chúng trong tranh."
- "Bài chưa được luyện tập trong 18 ngày; học sinh chưa nộp bài tập về nhà nên không có bằng chứng ghi nhớ. Củng cố các từ về quần áo/mua sắm mà chẩn đoán xác định là chưa được kiểm chứng sau lớp học."

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
        qid = q.get("question_id")
        qid_disp = qid if qid is not None else f"fs-{i}"
        days = q.get("days_since")
        weak = q.get("weakness_score")
        meta = []
        if days is not None:
            meta.append(f"{days}d ago")
        if weak is not None:
            meta.append(f"weakness={weak:.2f}")
        if q.get("hw_status") == "not_attempted":
            meta.append("hw=chưa_làm_bài")
        meta_str = " | ".join(meta)
        media = "yes" if q.get("requires_media") else "no"
        n_stem = len(q.get("stem_media_urls") or [])
        n_com = len(q.get("comment_media_urls") or [])
        skill_hint = q.get("skill_hint", "other")
        comment = html.unescape((q.get("comment_plain") or "").strip())
        comment_str = f' comment="{comment[:100]}"' if comment else ""
        lines.append(
            f'[{q.get("signal_type", "?")}] MEDIA={media} stem_files={n_stem} comment_files={n_com} '
            f'skill_hint={skill_hint} '
            f'qid={qid_disp} lesson_id={q["lesson_id"]} '
            f'lesson_title="{q.get("lesson_title", "")}" '
            f'[{meta_str}] '
            f'type="{q["question_type"]}" '
            f'text="{(q.get("question_text") or "")[:120]}"'
            f'{comment_str} '
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


def enrich_homework_from_pool(homework: list, question_pool: list) -> None:
    """
    Attach authoritative media + metadata from the pool (by lesson_id + question_id).
    Avoids asking the model to echo long URLs; keeps requires_media aligned with export.
    """
    by_key: dict[tuple, dict] = {}
    for q in question_pool:
        lid = q.get("lesson_id")
        qid = q.get("question_id")
        if lid is None or qid is None:
            continue
        by_key[(int(lid), int(qid))] = q

    for row in homework:
        lid = row.get("lesson_id")
        qid = row.get("question_id")
        if lid is None or qid is None:
            continue
        src = by_key.get((int(lid), int(qid)))
        if not src:
            continue
        row["requires_media"] = bool(src.get("requires_media"))
        row["stem_media_urls"] = list(src.get("stem_media_urls") or [])
        row["comment_media_urls"] = list(src.get("comment_media_urls") or [])
        if src.get("choice_previews") is not None:
            row["choice_previews"] = list(src.get("choice_previews") or [])
        if src.get("comment_plain"):
            row["comment_plain"] = src.get("comment_plain")
        if src.get("question_folder"):
            row["question_folder"] = src.get("question_folder")


def _run_selector_via_responses(
    diagnostic_text: str,
    question_pool: list,
    client: OpenAI,
    model: str,
    save_path: str | None,
) -> list:
    """Models like gpt-5.4-pro: /v1/responses + json_schema trong text.format."""
    prompt = build_prompt(diagnostic_text, question_pool)
    req: dict = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": HOMEWORK_SCHEMA["name"],
                "strict": HOMEWORK_SCHEMA["strict"],
                "schema": HOMEWORK_SCHEMA["schema"],
            }
        },
    }
    if openai_responses_include_temperature(model):
        req["temperature"] = 0
    response = client.responses.create(**req)
    raw = response.output_text
    homework = parse_response(raw)
    enrich_homework_from_pool(homework, question_pool)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework


def run_selector(
    diagnostic_text: str,
    question_pool: list,
    client: OpenAI | None = None,
    save_path: str | None = None,
    model: str = DEFAULT_HOMEWORK_MODEL,
) -> list:
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    if openai_uses_responses_api(model):
        return _run_selector_via_responses(
            diagnostic_text, question_pool, client, model, save_path
        )

    prompt = build_prompt(diagnostic_text, question_pool)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_schema", "json_schema": HOMEWORK_SCHEMA},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content
    homework = parse_response(raw)
    enrich_homework_from_pool(homework, question_pool)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework
