"""
Diagnostic agent — GPT-4o, plain text output.

Input:  summary dict + tiered_candidates list
Output: plain Vietnamese analysis string (~500-700 words)

The output is intentionally NOT structured JSON. It serves as a rich
chain-of-thought briefing for the selector agent.
"""

from __future__ import annotations

import os

from openai import OpenAI

from agents.model_config import DEFAULT_HOMEWORK_MODEL

SYSTEM_PROMPT = """\
Bạn là chuyên gia chẩn đoán học tiếng Anh, phân tích dữ liệu kết quả học tập \
của một học sinh người Việt. Học sinh đang ở Phase 0, cấp độ 4–5.

Giải thích các trường dữ liệu:
- hw_status=attempted: học sinh đã nộp bài tập cho bài học này — "Failed questions" phản ánh lỗi thực tế.
- hw_status=not_attempted: học sinh đã học trên lớp nhưng CHƯA NỘP BÀI TẬP VỀ NHÀ — \
không có dữ liệu lỗi cụ thể; "Question bank preview" chỉ là mẫu câu hỏi trong ngân hàng bài tập. \
Đây là rủi ro học tập cao vì không có bằng chứng ghi nhớ sau lớp học.

Trước khi viết phân tích, hãy xác định 3 mẫu lỗi hoặc rủi ro nghiêm trọng nhất bạn quan sát được \
(bao gồm cả các bài chưa làm bài tập), sau đó trình bày chi tiết từng mẫu trong các đoạn văn rõ ràng. \
Viết bằng tiếng Việt. Không dùng JSON, không dùng danh sách bullet, không dùng markdown headers. \
Kết quả phân tích của bạn sẽ được đọc bởi một agent chọn câu hỏi như một tài liệu tóm tắt.\
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
[{signal_type_upper}] "{title}" | hw_status={hw_status} | weakness={weakness:.2f} | {days}d ago | {q_count} usable questions
  Weak skills: {skills}
  {content_label}: {content_info}
  Worst speaking: {worst_sp}\
"""


def _fmt_preview_q(questions: list) -> str:
    if not questions:
        return "not available"
    textable = [q for q in questions if not q.get("requires_media") and q.get("question_text")]
    if not textable:
        media_count = len(questions)
        return f"all {media_count} preview question(s) require audio/image media"
    parts = []
    for q in textable[:3]:
        parts.append(f'"{q.get("question_text", "")[:80]}" (type: {q.get("question_type", "")})')
    return " | ".join(parts)


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
        hw_status = c.get("homework_status", "attempted")
        if hw_status == "not_attempted":
            content_label = "Question bank preview (chưa làm bài)"
            content_info = _fmt_preview_q(c.get("question_bank_preview") or [])
        else:
            content_label = "Failed questions"
            content_info = _fmt_failed_q(c.get("failed_text_questions") or [])
        block = LESSON_BLOCK_TEMPLATE.format(
            signal_type_upper=c.get("signal_type", "").upper(),
            title=c.get("title", ""),
            hw_status=hw_status,
            weakness=c.get("weakness_score", 0),
            days=c.get("days_since_last_practice", 0),
            q_count=c.get("usable_question_count", 0),
            skills=", ".join(c.get("weak_skills") or []) or "none identified",
            content_label=content_label,
            content_info=content_info,
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
    model: str = DEFAULT_HOMEWORK_MODEL,
) -> str:
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    prompt = build_prompt(summary, candidates)

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""
