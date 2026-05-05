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
from collections import defaultdict

from openai import OpenAI

from agents.model_config import (
    DEFAULT_HOMEWORK_MODEL,
    openai_responses_include_temperature,
    openai_uses_responses_api,
)

MAX_SELECTOR_RETRIES = 2

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
                        "speaking_evidence",
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
                        "speaking_evidence": {"anyOf": [{"type": "string"}, {"type": "null"}]},
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
- Tier diversity: if the pool contains ≥2 questions from spaced_rep lessons, you MUST include \
at least 2 of them in the final 15.
- Speaking: include at least the number shown in REQUIRED MINIMUMS in the user message.
- Include at least: 4 grammar or fill-blank, 3 vocabulary
- Per-lesson cap: pick at most 2 questions from any single lesson. If two questions come from \
the same lesson, they MUST have different skill_category values.
  BAD: grammar + grammar from lesson 3528960 → VIOLATES the rule.
  GOOD: grammar + speaking from lesson 3528960 → OK.
- SELF-CHECK — run all three checks in order before submitting:
  1. Count occurrences per lesson_id. Any lesson appearing >2 times → drop the excess, \
replace with questions from different lessons.
  2. For every lesson appearing exactly twice: verify the two skill_category values differ. \
If SAME skill (e.g. grammar + grammar) → replace one question: choose a different skill_hint \
row from that same lesson, or pick from a different lesson entirely.
  3. Count MEDIA=yes. If total > 4 → drop the excess.
- Tie-break: prefer fill-blank > multiple-choice > speaking when signal_type and lesson are equal
- MEDIA — HARD LIMIT: at most 4 questions with MEDIA=yes total across all 15 selections. \
Count MEDIA=yes selections before finalising; if you have more than 4, drop the excess. \
Set requires_media=true for MEDIA=yes pool lines and requires_media=false for all others. \
For free-speaking pool rows (no question_id) use question_id=null and requires_media=false.
- Use the skill_hint field on each pool line to guide skill_category assignment; \
map "other" to whichever of grammar/vocabulary/speaking best fits the question_text.

REASON FIELD RULES — this is the most important field:
Write 1–2 sentences per question IN VIETNAMESE that are specific to THIS student's actual performance.
Every reason MUST explicitly state how many days ago the lesson was last practiced \
(e.g. "bài này đã học 118 ngày trước — cần ôn lại từ đầu"). The days value is shown \
as "{N}d ago" on every pool line.
Also reference at least one of: a specific wrong answer they gave, a speaking transcript \
(e.g. "học sinh nói 'It's black' thay vì 'It's blue'"), a speaking score from speaking_scores \
(e.g. "brainstorm=0/100"), or a named error pattern from the diagnostic.
If the pool line shows prev_wrong=yes, you MUST cite that specific mistake in the reason field. \
State it as: 'Học sinh đã trả lời sai câu này trước đó: điền/chọn "[student_ans]" thay vì "[correct_ans]".' \
Do NOT omit this when prev_wrong=yes — it is the primary evidence for selecting this question.
Do NOT write generic labels like "critical signal, grammar practice".
Do NOT invent errors that are not present in the pool data or diagnostic.
The reason field MUST be written entirely in Vietnamese.

SPEAKING_EVIDENCE FIELD:
Set speaking_evidence to the exact short fragment of the student's transcript you cited in the reason \
(e.g. "I'm a last in karaoke", "Can see a bus stop"). This allows the UI to highlight exactly that \
transcript. Rules:
- If your reason quotes or paraphrases a specific student speaking utterance → set speaking_evidence \
to the exact quoted text from that utterance (copy it verbatim from the diagnostic or pool data).
- If your reason does NOT reference any specific speaking transcript → set speaking_evidence to null.
- Never fabricate a transcript fragment not found in the diagnostic or pool data.

Good reason examples (in Vietnamese):
- "Học sinh điền 'cost' thay vì 'is' trong bài fill-blank này — lỗi chia động từ theo chủ ngữ xuất hiện ở 3 bài học khác nhau theo kết quả chẩn đoán. Bài đã học cách đây 20 ngày (đã quên hoàn toàn)."
- "Điểm brainstorm 0/100 trong bài này: học sinh nói 'Can see a bus stop, a train station' khi được yêu cầu liệt kê 4 targets — thiếu 'bus' và 'train' dù đã thấy chúng trong tranh. Bài học đã qua 118 ngày."
- "Bài chưa được luyện tập trong 18 ngày; học sinh chưa nộp bài tập về nhà nên không có bằng chứng ghi nhớ. Củng cố các từ về quần áo/mua sắm mà chẩn đoán xác định là chưa được kiểm chứng sau lớp học."

Return ONLY valid JSON matching the schema. No markdown, no explanation.\
"""

USER_TEMPLATE = """\
DIAGNOSTIC ANALYSIS
-------------------
{diagnostic_text}

QUESTION POOL ({count} questions available)
REQUIRED MINIMUMS: ≥{min_speaking} speaking | ≥4 grammar/fill-blank | ≥3 vocabulary
--------------------------------------------
{pool_text}

Select exactly 15 questions. REQUIRED MINIMUMS: ≥{min_speaking} speaking | ≥4 grammar | ≥3 vocabulary. \
Assign question_no 1–15 in order of priority.\
"""

_RETRY_TEMPLATE = """\
⚠️ CONSTRAINT VIOLATIONS — your previous answer broke these hard rules:
{violations_text}

Fix ALL violations above before submitting. These are hard constraints, not suggestions.
- diff_skill violation: for the listed lesson, replace one question with one that has \
a DIFFERENT skill_category (consult the pool below for alternatives).
- grammar deficit: swap in grammar questions until you reach ≥4 total.
- speaking deficit: swap in speaking questions until you reach ≥{min_speaking} total.
- media excess: set requires_media=false for questions beyond the first 4 MEDIA=yes.

DIAGNOSTIC ANALYSIS
-------------------
{diagnostic_text}

QUESTION POOL ({count} questions available)
REQUIRED MINIMUMS: ≥{min_speaking} speaking | ≥4 grammar/fill-blank | ≥3 vocabulary
--------------------------------------------
{pool_text}

Select exactly 15 questions. REQUIRED MINIMUMS: ≥{min_speaking} speaking | ≥4 grammar | ≥3 vocabulary. \
Assign question_no 1–15 in order of priority.\
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
        prev_str = ""
        if q.get("prev_student_answer") is not None:
            prev_str = (
                f' prev_wrong=yes'
                f' student_ans="{q["prev_student_answer"]}"'
                f' correct_ans="{q["prev_correct_answer"]}"'
            )
        lines.append(
            f'[{q.get("signal_type", "?")}] MEDIA={media} stem_files={n_stem} comment_files={n_com} '
            f'skill_hint={skill_hint} '
            f'qid={qid_disp} lesson_id={q["lesson_id"]} '
            f'lesson_title="{q.get("lesson_title", "")}" '
            f'[{meta_str}] '
            f'type="{q["question_type"]}" '
            f'text="{(q.get("question_text") or "")[:120]}"'
            f'{comment_str}'
            f'{prev_str} '
            f'answer="{q.get("correct_answer") or "open"}"'
        )
    return "\n".join(lines)


def build_prompt(diagnostic_text: str, question_pool: list, min_speaking: int = 3) -> str:
    return USER_TEMPLATE.format(
        diagnostic_text=diagnostic_text,
        count=len(question_pool),
        pool_text=_pool_to_text(question_pool),
        min_speaking=min_speaking,
    )


def _build_retry_prompt(
    diagnostic_text: str,
    question_pool: list,
    violations: list[str],
    min_speaking: int,
) -> str:
    violations_text = "\n".join(f"  • {v}" for v in violations)
    return _RETRY_TEMPLATE.format(
        violations_text=violations_text,
        diagnostic_text=diagnostic_text,
        count=len(question_pool),
        pool_text=_pool_to_text(question_pool),
        min_speaking=min_speaking,
    )


def _validate_constraints(homework: list, min_speaking: int) -> list[str]:
    violations: list[str] = []
    by_lesson: dict = defaultdict(list)
    for q in homework:
        by_lesson[q["lesson_id"]].append(q)
    for lid, qs in by_lesson.items():
        if len(qs) > 2:
            nos = [q["question_no"] for q in qs]
            violations.append(f"lesson {lid}: {len(qs)} questions (max 2) — q{nos}")
        elif len(qs) == 2 and qs[0]["skill_category"] == qs[1]["skill_category"]:
            violations.append(
                f"lesson {lid}: q{qs[0]['question_no']} and q{qs[1]['question_no']} "
                f"both skill_category={qs[0]['skill_category']} (must differ)"
            )
    grammar_count = sum(1 for q in homework if q["skill_category"] == "grammar")
    if grammar_count < 4:
        violations.append(f"only {grammar_count} grammar questions (need ≥4)")
    vocab_count = sum(1 for q in homework if q["skill_category"] == "vocabulary")
    if vocab_count < 3:
        violations.append(f"only {vocab_count} vocabulary questions (need ≥3)")
    speaking_count = sum(1 for q in homework if q["skill_category"] == "speaking")
    if speaking_count < min_speaking:
        violations.append(f"only {speaking_count} speaking questions (need ≥{min_speaking})")
    media_count = sum(1 for q in homework if q.get("requires_media"))
    if media_count > 4:
        violations.append(f"{media_count} MEDIA=yes questions (max 4)")
    return violations


def _repair_homework(homework: list, question_pool: list, min_speaking: int) -> list:
    """
    Deterministic post-processing repair applied when retries are exhausted.
    Fixes violations in dependency order so earlier steps don't undo later ones.
    Repaired questions receive a Vietnamese placeholder reason field.
    """
    from collections import Counter

    homework = [dict(q) for q in homework]

    sorted_pool = sorted(
        question_pool,
        key=lambda q: (-(q.get("weakness_score") or 0), -(q.get("days_since") or 0)),
    )

    def _make_row(pq: dict, question_no: int) -> dict:
        return {
            "question_no": question_no,
            "lesson_id": pq["lesson_id"],
            "lesson_title": pq.get("lesson_title", ""),
            "skill_category": pq.get("skill_hint", "other"),
            "question_type": pq.get("question_type", ""),
            "question_text": pq.get("question_text", ""),
            "correct_answer": pq.get("correct_answer"),
            "difficulty": pq.get("difficulty", "medium"),
            "reason": "[Câu được điều chỉnh tự động để đảm bảo đa dạng bài học.]",
            "question_id": pq.get("question_id"),
            "requires_media": bool(pq.get("requires_media")),
            "speaking_evidence": None,
        }

    def _find(
        idx: int,
        exclude_lesson=None,
        require_skill=None,
        exclude_skills=None,
    ) -> dict | None:
        """Return best pool question to replace homework[idx].

        Respects per-lesson cap and prefers placements that don't create new
        diff_skill violations. Falls back to violation-creating placements only
        if no clean option exists.
        """
        occupied = {
            (q.get("lesson_id"), q.get("question_id"))
            for i, q in enumerate(homework) if i != idx
        }
        counts = Counter(q["lesson_id"] for i, q in enumerate(homework) if i != idx)
        skills_in_lesson: dict = defaultdict(set)
        for i, q in enumerate(homework):
            if i != idx:
                skills_in_lesson[q["lesson_id"]].add(q["skill_category"])

        fallback = None
        for pq in sorted_pool:
            key = (pq.get("lesson_id"), pq.get("question_id"))
            if key in occupied:
                continue
            lid = pq.get("lesson_id")
            if exclude_lesson and lid == exclude_lesson:
                continue
            if counts.get(lid, 0) >= 2:
                continue
            skill = pq.get("skill_hint", "other")
            if require_skill and skill != require_skill:
                continue
            if exclude_skills and skill in exclude_skills:
                continue
            # Prefer placements that don't create a new diff_skill violation
            if counts.get(lid, 0) == 1 and skill in skills_in_lesson.get(lid, set()):
                if fallback is None:
                    fallback = pq
                continue
            return pq
        return fallback

    def _by_lesson():
        d: dict = defaultdict(list)
        for i, q in enumerate(homework):
            d[q["lesson_id"]].append(i)
        return d

    # Step 1: per_lesson_le2 — iterate until stable
    changed = True
    while changed:
        changed = False
        for lid, indices in _by_lesson().items():
            if len(indices) > 2:
                idx = indices[-1]
                repl = _find(idx, exclude_lesson=lid)
                if repl:
                    homework[idx] = _make_row(repl, homework[idx]["question_no"])
                    changed = True
                    break  # restart after every swap

    # Step 2: diff_skill — loop until stable (fixing one pair may create another)
    for _ in range(10):
        made_change = False
        for lid, indices in _by_lesson().items():
            if len(indices) == 2:
                q0, q1 = homework[indices[0]], homework[indices[1]]
                if q0["skill_category"] == q1["skill_category"]:
                    repl = _find(indices[1], exclude_skills={q0["skill_category"]})
                    if repl:
                        homework[indices[1]] = _make_row(repl, q1["question_no"])
                        made_change = True
        if not made_change:
            break

    # Step 3: grammar ≥ 4
    grammar_count = sum(1 for q in homework if q["skill_category"] == "grammar")
    non_grammar = sorted(
        [i for i, q in enumerate(homework) if q["skill_category"] not in ("grammar", "speaking")],
        key=lambda i: -homework[i]["question_no"],
    )
    for idx in non_grammar:
        if grammar_count >= 4:
            break
        repl = _find(idx, require_skill="grammar")
        if repl:
            homework[idx] = _make_row(repl, homework[idx]["question_no"])
            grammar_count += 1

    # Step 4: vocabulary ≥ 3
    vocab_count = sum(1 for q in homework if q["skill_category"] == "vocabulary")
    non_vocab = sorted(
        [i for i, q in enumerate(homework)
         if q["skill_category"] not in ("grammar", "speaking", "vocabulary")],
        key=lambda i: -homework[i]["question_no"],
    )
    for idx in non_vocab:
        if vocab_count >= 3:
            break
        repl = _find(idx, require_skill="vocabulary")
        if repl:
            homework[idx] = _make_row(repl, homework[idx]["question_no"])
            vocab_count += 1

    # Step 5: speaking ≥ min_speaking
    speaking_count = sum(1 for q in homework if q["skill_category"] == "speaking")
    non_speaking = sorted(
        [i for i, q in enumerate(homework)
         if q["skill_category"] not in ("grammar", "speaking")],
        key=lambda i: -homework[i]["question_no"],
    )
    for idx in non_speaking:
        if speaking_count >= min_speaking:
            break
        repl = _find(idx, require_skill="speaking")
        if repl:
            homework[idx] = _make_row(repl, homework[idx]["question_no"])
            speaking_count += 1

    return homework


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
    min_speaking: int = 3,
) -> list:
    """Models like gpt-5.4-pro: /v1/responses + json_schema trong text.format."""
    prompt = build_prompt(diagnostic_text, question_pool, min_speaking=min_speaking)
    best_homework: list | None = None
    best_violation_count = 999

    for attempt in range(MAX_SELECTOR_RETRIES):
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

        violations = _validate_constraints(homework, min_speaking)
        if len(violations) < best_violation_count:
            best_homework = homework
            best_violation_count = len(violations)

        if not violations:
            break
        print(f"      [selector retry {attempt + 1}/{MAX_SELECTOR_RETRIES}] violations: {violations}")
        prompt = _build_retry_prompt(diagnostic_text, question_pool, violations, min_speaking)

    homework = best_homework  # type: ignore[assignment]
    remaining = _validate_constraints(homework, min_speaking)
    if remaining:
        print(f"      [selector repair] fixing {len(remaining)} remaining violations: {remaining}")
        homework = _repair_homework(homework, question_pool, min_speaking)
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
    min_speaking: int = 3,
) -> list:
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    if openai_uses_responses_api(model):
        return _run_selector_via_responses(
            diagnostic_text, question_pool, client, model, save_path,
            min_speaking=min_speaking,
        )

    prompt = build_prompt(diagnostic_text, question_pool, min_speaking=min_speaking)
    best_homework: list | None = None
    best_violation_count = 999

    for attempt in range(MAX_SELECTOR_RETRIES):
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

        violations = _validate_constraints(homework, min_speaking)
        if len(violations) < best_violation_count:
            best_homework = homework
            best_violation_count = len(violations)

        if not violations:
            break
        print(f"      [selector retry {attempt + 1}/{MAX_SELECTOR_RETRIES}] violations: {violations}")
        prompt = _build_retry_prompt(diagnostic_text, question_pool, violations, min_speaking)

    homework = best_homework  # type: ignore[assignment]
    remaining = _validate_constraints(homework, min_speaking)
    if remaining:
        print(f"      [selector repair] fixing {len(remaining)} remaining violations: {remaining}")
        homework = _repair_homework(homework, question_pool, min_speaking)
        enrich_homework_from_pool(homework, question_pool)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework
