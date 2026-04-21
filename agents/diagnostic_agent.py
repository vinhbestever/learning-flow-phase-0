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
            f"(correct: {q.get('correct_answer')}, "
            f"student: {q.get('student_answer')})"
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
    text = response.choices[0].message.content or ""

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

    return text
