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
- Worst speaking items gồm hai loại: \
[free_speaking] là nói mở / warmup (score=0 nghĩa là sai hoàn toàn; answer_type=inaccordant = câu trả lời không liên quan; \
answer_type=lack_of_knowledge = học sinh không biết); \
[conversation] là hội thoại cấu trúc (score<70/100 mới được ghi nhận là thất bại; \
"gram" = điểm ngữ pháp, "pron" = điểm phát âm — "expected" là câu trả lời mẫu).
- Forgetting curve: tất cả bài học đều chỉ có 1 lần luyện tập trước (stability ≈ 7 ngày). \
Bài học trên 21 ngày đạt forgetting_score ≥ 0.95 (gần như quên hoàn toàn); \
bài 7 ngày ≈ 0.63 (đã quên nhiều nhưng còn một phần). \
Sự khác biệt giữa 7 ngày và 30 ngày CÓ ý nghĩa — ưu tiên bài lâu hơn khi điểm yếu tương đương.
- Weak skills (viết): dựa trên accuracy < 70% trong bài tập LMS. Nếu rỗng, học sinh làm \
bài tập viết tốt — điểm yếu chủ yếu nằm ở kỹ năng nói (xem speaking_scores bên dưới).
- speaking_scores: điểm trung bình per-lesson từ các phiên Digital Teacher. \
Thang điểm free_speaking: 0–1 (nhân 100 để so sánh). \
Conversation và pronunciation: 0–100.

QUAN TRỌNG — Selection bias trong "LESSONS TO REVIEW": \
Danh sách bài cần ôn được chọn có chủ đích là các bài YẾU NHẤT hoặc LÂU NHẤT chưa ôn. \
Vì vậy, việc free_speaking=0/100 xuất hiện nhiều trong các bài cần ôn là CÓ CHỦ Ý — \
đó là lý do chúng được chọn vào danh sách, KHÔNG có nghĩa học sinh yếu free_speaking trên toàn bộ chương trình. \
Hãy tham chiếu "Free speaking / warmup avg" và "Free speaking lesson breakdown" trong STUDENT SUMMARY \
để đánh giá mức độ thực tế. Nếu global avg > 50 nhưng các bài cần ôn đều = 0, \
nhận định đúng là "học sinh có nhiều bài free_speaking tốt nhưng còn {N} bài cụ thể cần ôn lại". \
Tránh tổng quát hóa từ danh sách bài cần ôn sang toàn bộ khả năng của học sinh.

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
Free speaking / warmup avg: {free}/100{free_flag}
  Free speaking lesson breakdown: {fs_lesson_breakdown}
Conversation avg:  {convo}/100
Free speaking answer distribution: {answer_dist}
Critical speaking weaknesses: {critical_speaking}

Homework skill breakdown (writing accuracy by category):
{skill_breakdown}

{forgetting_note}

LESSONS TO REVIEW
-----------------
Note: the lessons below are selected because they have the HIGHEST weakness or forgetting scores. \
A lesson appearing here with free_speaking=0 reflects a specific weak attempt, \
not the student's overall speaking ability (see breakdown above).

{lesson_blocks}

Analyze: identify skill gaps, recurring error patterns across lessons, which \
lessons need deep practice vs light reinforcement, and what question types \
are most effective per lesson.\
"""

LESSON_BLOCK_TEMPLATE = """\
[{signal_type_upper}] "{title}" | hw_status={hw_status} | weakness={weakness:.2f} | {days}d ago | {q_count} usable questions
  Speaking scores: {speaking_summary}
  Weak skills (writing): {skills}
  {content_label}: {content_info}{media_failed}
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


_SPEAKING_TYPES = {"free_speaking", "conversation"}


def _fmt_speaking(items: list) -> str:
    # Only include free_speaking and conversation — brainstorm items are not
    # interpretable by the agent and should not influence the diagnostic.
    items = [s for s in items if s.get("lms_type") in _SPEAKING_TYPES]
    if not items:
        return "none"
    parts = []
    for s in items[:3]:
        lms_type = s.get("lms_type", "free_speaking")
        q = (s.get("question") or "")[:60]
        transcript = (s.get("user_transcript") or "")[:60]
        score = s.get("score")
        if lms_type == "conversation":
            gram = s.get("grammar_score")
            pron = s.get("pronunciation_score")
            expected = (s.get("expected_answer") or "")[:60]
            detail = f"score={score}/100 gram={gram} pron={pron}"
            if expected:
                detail += f' expected="{expected}"'
        else:
            answer_type = s.get("answer_type") or "?"
            detail = f"score={score} [{answer_type}] warmup"
        parts.append(f'[{lms_type}] Q: "{q}" → "{transcript}" {detail}')
    return " | ".join(parts)


def _fmt_speaking_scores(scores: dict) -> str:
    """Format per-lesson speaking averages into a readable summary."""
    if not scores:
        return "no data"
    parts = []
    free_avg = scores.get("free_speaking_avg")
    free_n = scores.get("free_speaking_attempts", 0)
    if free_n:
        pct = round(free_avg * 100) if free_avg is not None else "?"
        # Add a clarifying note when avg=0 with very few attempts so the agent
        # does not over-interpret a single failed warmup as a deep skill gap.
        if pct == 0 and free_n <= 2:
            note = f" (chỉ {free_n} câu warmup duy nhất bị fail — không đủ mẫu)"
        else:
            note = f" ({free_n} attempts)"
        parts.append(f"free_speaking={pct}/100{note}")
    convo_avg = scores.get("conversation_avg")
    convo_n = scores.get("conversation_attempts", 0)
    if convo_n:
        val = round(convo_avg) if convo_avg is not None else "?"
        parts.append(f"conversation={val}/100 ({convo_n} attempts)")
    pron_avg = scores.get("pronunciation_avg")
    pron_n = scores.get("pronunciation_attempts", 0)
    if pron_n:
        val = round(pron_avg) if pron_avg is not None else "?"
        parts.append(f"pronunciation={val}/100 ({pron_n} attempts)")
    return ", ".join(parts) if parts else "no speaking activity recorded"


def _fmt_skill_breakdown(breakdown: dict) -> str:
    if not breakdown:
        return "  (no homework data)"
    lines = []
    for folder, stats in breakdown.items():
        acc = stats.get("accuracy")
        total = stats.get("total", 0)
        correct = stats.get("correct", 0)
        acc_str = f"{acc:.1%}" if acc is not None else "N/A"
        lines.append(f"  {folder}: {correct}/{total} correct ({acc_str})")
    return "\n".join(lines)


def build_prompt(summary: dict, candidates: list) -> str:
    by_status = summary.get("lessons_by_status", {})
    completed = by_status.get("completed", 0)
    total = summary.get("total_lessons", 0)

    skill_breakdown_text = _fmt_skill_breakdown(
        summary.get("overall_homework_skill_breakdown", {})
    )
    forgetting_note = summary.get(
        "forgetting_curve_note",
        "Forgetting curve: lessons older than 7 days are considered fully forgotten.",
    )

    lesson_blocks = []
    for c in candidates:
        hw_status = c.get("homework_status", "attempted")
        if hw_status == "not_attempted":
            content_label = "Question bank preview (chưa làm bài)"
            content_info = _fmt_preview_q(c.get("question_bank_preview") or [])
        else:
            content_label = "Failed questions"
            content_info = _fmt_failed_q(c.get("failed_text_questions") or [])

        media_failed_count = c.get("failed_media_questions_count", 0)
        media_failed = (
            f"\n  (+{media_failed_count} media-only failed questions not shown inline)"
            if media_failed_count
            else ""
        )

        block = LESSON_BLOCK_TEMPLATE.format(
            signal_type_upper=c.get("signal_type", "").upper(),
            title=c.get("title", ""),
            hw_status=hw_status,
            weakness=c.get("weakness_score", 0),
            days=c.get("days_since_last_practice", 0),
            q_count=c.get("usable_question_count", 0),
            speaking_summary=_fmt_speaking_scores(c.get("speaking_scores", {})),
            skills=", ".join(c.get("weak_skills") or []) or "none (writing accuracy is good)",
            content_label=content_label,
            content_info=content_info,
            media_failed=media_failed,
            worst_sp=_fmt_speaking(c.get("worst_speaking_items") or []),
        )
        lesson_blocks.append(block)

    free_val = summary.get("overall_free_speaking_score_avg")
    critical_speaking = summary.get("critical_speaking_types") or []
    free_flag = " ⚠️ YẾU (dưới ngưỡng 50/100)" if (free_val is not None and free_val < 50) else ""
    critical_speaking_str = (
        ", ".join(critical_speaking) if critical_speaking
        else "none (writing is the main weakness)"
    )

    # Use the pre-computed distribution injected by context_builder._inject_fs_distribution
    # which covers ALL scored_candidates (not just the top-15 tiered ones) — this gives
    # the LLM the full picture to avoid over-generalizing from the weakest bài list.
    fs_dist = summary.get("free_speaking_lesson_dist") or {}
    fs_good = fs_dist.get("good", 0)
    fs_partial = fs_dist.get("partial", 0)
    fs_zero = fs_dist.get("zero", 0)
    fs_total = fs_dist.get("total", 0)
    if fs_total:
        fs_lesson_breakdown = (
            f"{fs_good} bài đạt (≥80/100), "
            f"{fs_partial} bài trung bình, "
            f"{fs_zero} bài yếu (=0/100) "
            f"— trong tổng {fs_total} bài có free_speaking"
        )
    else:
        fs_lesson_breakdown = "không có dữ liệu"

    return USER_TEMPLATE.format(
        completed=completed,
        total=total,
        pron=summary.get("overall_pronunciation_score_avg", "N/A"),
        free=free_val if free_val is not None else "N/A",
        free_flag=free_flag,
        fs_lesson_breakdown=fs_lesson_breakdown,
        convo=summary.get("overall_conversation_score_avg", "N/A"),
        answer_dist=summary.get("overall_free_speaking_answer_type_dist", {}),
        critical_speaking=critical_speaking_str,
        skill_breakdown=skill_breakdown_text,
        forgetting_note=forgetting_note,
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
