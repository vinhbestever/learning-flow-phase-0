import json

from ..lms_question_rich import rich_question_fields
from ..preprocess import extract_question_content
from .text import has_media, strip_html


def extract_lms_question(row: dict) -> dict:
    qt = row.get("question_type", "")
    raw_content = row.get("content") or ""
    raw_answers = row.get("answers") or "[]"

    question_text = strip_html(raw_content)
    requires_media = has_media(raw_content)

    try:
        answers = json.loads(raw_answers)
    except Exception:
        answers = []
    correct_answer = None

    if qt == "Điền vào chỗ trống":
        if isinstance(answers, list):
            correct_parts = [
                str(a.get("is_true") or a.get("option") or "").strip()
                for a in answers
                if isinstance(a, dict)
            ]
            correct_answer = " / ".join(p for p in correct_parts if p) or None

    elif qt == "Trả lời bằng giọng nói":
        if isinstance(answers, list) and answers:
            a0 = answers[0]
            if isinstance(a0, str):
                correct_answer = a0.strip() or None
            elif isinstance(a0, dict):
                correct_answer = strip_html(a0.get("content") or a0.get("content_text") or "") or None
                requires_media = requires_media or has_media(a0.get("content", ""))

    elif qt in ("Một lựa chọn", "Nhiều lựa chọn"):
        if isinstance(answers, list):
            correct_items = [
                a
                for a in answers
                if isinstance(a, dict)
                and (
                    a.get("is_true") is True
                    or str(a.get("is_true", "")).lower() == "true"
                    or (
                        isinstance(a.get("is_true"), str)
                        and a["is_true"].upper() in ("A", "B", "TRUE", "ĐÚNG")
                    )
                )
            ]
            if correct_items:
                ca_text = strip_html(correct_items[0].get("content") or correct_items[0].get("content_text") or "")
                if has_media(correct_items[0].get("content", "")):
                    requires_media = True
                correct_answer = ca_text or None

    elif qt == "Xứng-Hợp":
        if isinstance(answers, dict):
            col1 = answers.get("column1") or []
            col2 = answers.get("column2") or []
            pairs = []
            for a in col1:
                if not isinstance(a, dict):
                    continue
                c1_text = strip_html(a.get("content", ""))
                correct_idx = int(a.get("is_true", 0))
                c2_item = col2[correct_idx - 1] if 0 < correct_idx <= len(col2) else {}
                c2_text = strip_html(c2_item.get("content", "")) if isinstance(c2_item, dict) else ""
                pairs.append(f"{c1_text}→{c2_text}" if c2_text else c1_text)
            correct_answer = "; ".join(p for p in pairs if p) or None
            if any(has_media(a.get("content", "")) for a in col2 if isinstance(a, dict)):
                requires_media = True

    elif qt == "Kéo thả vào chỗ trống trong đoạn văn":
        if isinstance(answers, dict):
            correct_answer = strip_html(answers.get("correctAnswer", "")) or None
            col2 = answers.get("column2", [])
            pieces = [
                a.get("content_text") or a.get("content") or strip_html(a.get("raw_content", ""))
                for a in col2
                if isinstance(a, dict)
            ]
            if pieces:
                question_text = (question_text or "Reorder") + ": " + " | ".join(p for p in pieces if p)

    rich = rich_question_fields(
        row,
        stem_html=raw_content,
        question_type=qt,
        raw_answers=raw_answers,
    )
    comment_raw = row.get("comment") or ""
    comment_plain = strip_html(comment_raw) or None
    payload = {
        "question_id": row.get("question_id"),
        "question_folder": row.get("question_folder"),
        "question_type": qt,
        "question_text": question_text or None,
        "comment_plain": comment_plain,
        "requires_media": requires_media,
        "correct_answer": correct_answer,
        **rich,
    }
    _sub = extract_question_content(row).get("student_answer")
    if _sub is not None and _sub != "" and _sub != []:
        payload["student_answer"] = _sub
    if row.get("is_correct") is not None:
        try:
            payload["is_correct"] = int(row["is_correct"])
        except (TypeError, ValueError):
            pass
    if row.get("result_id") is not None:
        payload["detail_result_id"] = row.get("result_id")
    return payload


def _detail_rows_for_practice(lms_id, detail_by_pid):
    rows = list(detail_by_pid.get(lms_id) or [])
    rows.sort(key=lambda x: (x.get("question_id") or 0, x.get("id") or 0))
    return rows


def build_homework_practice(
    lms_id,
    pr_by_pid,
    detail_by_pid,
    section_meta=None,
    bank_by_pid=None,
):
    """
    Homework for one section from tutor lms_id.

    Fills `questions` from the student's lms_practice_result_detail when present. Otherwise
    uses the practice catalogue in `data/practice_question_bank.json` (keyed by practice_id).
    Still returns a non-null object (tutor metadata + maybe empty `questions` if no source).
    """
    if not lms_id:
        return None
    bank_by_pid = bank_by_pid or {}
    r = pr_by_pid.get(lms_id)
    detail_rows = _detail_rows_for_practice(lms_id, detail_by_pid)
    if detail_rows:
        rows = detail_rows
        questions_source = "lms_practice_result_detail"
    else:
        rows = list(bank_by_pid.get(lms_id) or [])
        questions_source = "practice_question_bank" if rows else "none"
    questions = [extract_lms_question(row) for row in rows]
    meta = section_meta or {}
    has_student_detail = bool(detail_rows)
    has_lms_attempt = bool(r or has_student_detail)
    tot = None
    if r:
        tot = r.get("total_question")
    if tot is None and questions:
        tot = len(questions)
    if tot is None and meta.get("lms_num_question") is not None:
        tot = int(meta["lms_num_question"])
    return {
        "practice_id": lms_id,
        "lms_num_question": meta.get("lms_num_question"),
        "completed_lesson": meta.get("completed_lesson"),
        "has_lms_attempt": has_lms_attempt,
        "questions_source": questions_source,
        "score": r["diem_thi"] if r else None,
        "correct": r["total_correct_question"] if r else None,
        "total": tot,
        "submitted_date": (r.get("create_date") or "")[:10] if r else None,
        "questions": questions,
    }
