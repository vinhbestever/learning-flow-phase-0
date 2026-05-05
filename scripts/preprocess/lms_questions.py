import json
import re as _re
from collections import defaultdict

from ..lms_question_rich import rich_question_fields
from . import config


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode common HTML entities."""
    text = _re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&atilde;", "ã").replace("&aacute;", "á")
    text = text.replace("&agrave;", "à").replace("&acirc;", "â")
    text = _re.sub(r"\s+", " ", text).strip()
    return text


def _has_media(raw_html: str) -> bool:
    """True if the HTML contains image or audio elements."""
    return bool(_re.search(r"<(img|audio|source)\b", raw_html or "", _re.IGNORECASE))


def extract_question_content(row: dict) -> dict:
    """
    Extract human-readable question content from a detail record.

    Returns a dict with:
      question_text:   cleaned text of the question prompt
      correct_answer:  correct answer as plain text (None if image/audio only)
      student_answer:  what the student submitted
      requires_media:  True if the question depends on image/audio to make sense
    """
    qt = row.get("question_type", "")
    raw_content = row.get("content") or ""
    raw_answers = row.get("answers") or "[]"
    raw_bai_lam = row.get("bai_lam") or "[]"

    question_text = _strip_html(raw_content)
    requires_media = _has_media(raw_content)

    try:
        answers = json.loads(raw_answers)
    except Exception:
        answers = []

    try:
        bai_lam = json.loads(raw_bai_lam)
        student_items = [item for item in bai_lam if isinstance(item, dict)]
    except Exception:
        student_items = []

    correct_answer = None
    student_ans = None

    if qt == "Điền vào chỗ trống":
        if isinstance(answers, list):
            correct_parts = [
                str(a.get("is_true") or a.get("option") or "").strip()
                for a in answers if isinstance(a, dict)
            ]
            correct_answer = " / ".join(p for p in correct_parts if p) or None
            student_parts = [item.get("u") or "" for item in student_items[: len(answers)]]
            student_ans = " / ".join(p for p in student_parts if p) or None

    elif qt == "Trả lời bằng giọng nói":
        if isinstance(answers, list) and answers:
            a0 = answers[0]
            if isinstance(a0, str):
                correct_answer = a0.strip() or None
            elif isinstance(a0, dict):
                correct_answer = (
                    _strip_html(a0.get("content") or a0.get("content_text") or "") or None
                )
                requires_media = requires_media or _has_media(a0.get("content", ""))
        student_ans = student_items[0].get("u") if student_items else None

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
                ca = correct_items[0]
                ca_text = _strip_html(ca.get("content") or ca.get("content_text") or "")
                if _has_media(ca.get("content", "")):
                    requires_media = True
                correct_answer = ca_text or None

            selected_texts = []
            for i, item in enumerate(student_items):
                if item.get("u") == "1" and i < len(answers):
                    a = answers[i]
                    if isinstance(a, dict):
                        txt = _strip_html(a.get("content") or a.get("content_text") or "")
                        if _has_media(a.get("content", "")):
                            requires_media = True
                        selected_texts.append(txt or f"option_{i + 1}")
                    elif isinstance(a, str):
                        selected_texts.append(a)
            student_ans = (
                selected_texts[0]
                if (qt == "Một lựa chọn" and selected_texts)
                else (selected_texts or None)
            )

    elif qt == "Xứng-Hợp":
        if isinstance(answers, dict):
            col1 = answers.get("column1", [])
            col2 = answers.get("column2", [])
            if any(_has_media(a.get("content", "")) for a in col2 if isinstance(a, dict)):
                requires_media = True
            correct_pairs = []
            for i, a in enumerate(col1):
                if not isinstance(a, dict):
                    continue
                c1_text = _strip_html(a.get("content", "")) or f"item_{i + 1}"
                correct_idx = int(a.get("is_true", 0))
                c2_item = col2[correct_idx - 1] if 0 < correct_idx <= len(col2) else {}
                c2_text = _strip_html(c2_item.get("content", "")) if isinstance(c2_item, dict) else ""
                correct_pairs.append(f"{c1_text}→{c2_text}" if c2_text else c1_text)
            correct_answer = "; ".join(correct_pairs) or None
            wrong_terms = []
            for i, item in enumerate(student_items):
                if item.get("is_correct") == 0 and i < len(col1):
                    c1 = col1[i]
                    c1_text = _strip_html(c1.get("content", "")) if isinstance(c1, dict) else ""
                    wrong_terms.append(c1_text or f"item_{i + 1}")
            student_ans = f"wrong: {', '.join(wrong_terms)}" if wrong_terms else None

    elif qt == "Kéo thả vào chỗ trống trong đoạn văn":
        if isinstance(answers, dict):
            correct_answer = _strip_html(answers.get("correctAnswer", "")) or None
            col2 = answers.get("column2", [])
            pieces = [
                a.get("content_text") or a.get("content") or _strip_html(a.get("raw_content", ""))
                for a in col2
                if isinstance(a, dict)
            ]
            if not question_text or "[{}]" in question_text:
                question_text = "Reorder: " + " | ".join(p for p in pieces if p)
            assembled = []
            for item in student_items:
                idx = int(item.get("u", 0))
                if 0 < idx <= len(col2) and isinstance(col2[idx - 1], dict):
                    piece = col2[idx - 1].get("content_text") or col2[idx - 1].get("content") or ""
                else:
                    piece = "?"
                assembled.append(piece)
            student_ans = "".join(assembled) or None

    else:
        student_ans = [item.get("u") for item in student_items] or None

    rich = rich_question_fields(
        row,
        stem_html=raw_content,
        question_type=qt,
        raw_answers=raw_answers,
    )
    comment_raw = row.get("comment") or ""
    comment_plain = _strip_html(comment_raw)[:500] if comment_raw else None
    out = {
        "question_text": question_text[:300] if question_text else None,
        "comment_plain": comment_plain or None,
        "correct_answer": correct_answer,
        "student_answer": student_ans,
        "requires_media": requires_media,
        **rich,
    }
    if row.get("is_correct") is not None:
        try:
            out["is_correct"] = int(row["is_correct"])
        except (TypeError, ValueError):
            pass
    return out


def build_lms_homework(tutor_entry, pr_by_pid, detail_by_pid, lms_to_link, question_bank_by_pid=None):
    bai_tap_meta = tutor_entry.get("Bài tập") or {}
    luyen_tap_meta = tutor_entry.get("Luyện tập") or {}

    def result_for(lms_id):
        if not lms_id:
            return None
        r = pr_by_pid.get(lms_id)
        if not r:
            return None
        return {
            "practice_id": lms_id,
            "score": r["diem_thi"],
            "correct": r["total_correct_question"],
            "total": r["total_question"],
            "submitted_date": (r.get("create_date") or "")[:10] or None,
        }

    bai_tap = result_for(bai_tap_meta.get("lms_id"))
    luyen_tap = result_for(luyen_tap_meta.get("lms_id"))

    skill_counts = defaultdict(lambda: {"correct": 0, "total": 0})
    for lms_entry in [bai_tap_meta, luyen_tap_meta]:
        pid = lms_entry.get("lms_id")
        if not pid:
            continue
        for row in detail_by_pid.get(pid, []):
            folder = row.get("question_folder") or "Unknown"
            skill_counts[folder]["total"] += 1
            if row.get("is_correct") == 1:
                skill_counts[folder]["correct"] += 1

    skill_breakdown = {
        folder: {
            "correct": c["correct"],
            "total": c["total"],
            "accuracy": round(c["correct"] / c["total"], 3) if c["total"] else None,
        }
        for folder, c in skill_counts.items()
    }
    weak_skills = [
        f
        for f, s in skill_breakdown.items()
        if s["accuracy"] is not None and s["accuracy"] < 0.70
    ]

    failed_questions = []
    for lms_entry in [bai_tap_meta, luyen_tap_meta]:
        pid = lms_entry.get("lms_id")
        if not pid:
            continue
        failed = [r for r in detail_by_pid.get(pid, []) if r.get("is_correct") == 0]
        for row in failed[: config.WORST_LMS_Q_LIMIT]:
            content = extract_question_content(row)
            failed_questions.append(
                {
                    "practice_id": pid,
                    "question_id": row.get("question_id"),
                    "question_folder": row.get("question_folder"),
                    "question_type": row.get("question_type"),
                    **content,
                }
            )
        if len(failed_questions) >= config.WORST_LMS_Q_LIMIT:
            break

    attempted = bai_tap is not None or luyen_tap is not None

    not_attempted_preview = {}
    if not attempted and question_bank_by_pid:
        for section_name, lms_entry in [("bai_tap", bai_tap_meta), ("luyen_tap", luyen_tap_meta)]:
            pid = lms_entry.get("lms_id")
            if not pid:
                continue
            bank_qs = (question_bank_by_pid.get(pid) or [])[: config.QUESTION_BANK_PREVIEW_LIMIT]
            if bank_qs:
                not_attempted_preview[section_name] = []
                for q in bank_qs:
                    content = extract_question_content(q)
                    not_attempted_preview[section_name].append(
                        {
                            "practice_id": pid,
                            "question_id": q.get("question_id"),
                            "question_folder": q.get("question_folder"),
                            "question_type": q.get("question_type"),
                            "status": "not_attempted",
                            **content,
                        }
                    )

    return {
        "attempted": attempted,
        "bai_tap": bai_tap,
        "luyen_tap": luyen_tap,
        "lms_ids": {
            "bai_tap": bai_tap_meta.get("lms_id"),
            "luyen_tap": luyen_tap_meta.get("lms_id"),
        },
        "skill_breakdown": skill_breakdown,
        "weak_skills": weak_skills,
        "worst_questions": failed_questions,
        "not_attempted_preview": not_attempted_preview,
    }
