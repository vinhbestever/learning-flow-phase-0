"""
Export all questions (in-class + homework) for each lesson the student has studied.

Output: output/questions_export.json

Structure per lesson:
  in_class:
    pronunciation_drills[]  - scripted phonetic exercises (expectedTranscript + student result)
    free_speaking[]         - open-ended speaking (question + transcript + score + answer_type)
    interactive[]           - NON_AUDIO exercises (single_choice, true_false, fill_paragraph, matching)
  homework:
    bai_tap{}               - graded homework practice (all questions)
    luyen_tap{}             - extra practice (all questions)
"""

import glob
import json
import re
from collections import defaultdict
from datetime import date

DATA_DIR = "data"
OUTPUT_FILE = "output/questions_export.json"
TODAY = date(2026, 4, 21)


# ---------------------------------------------------------------------------
# Loaders (same as preprocess.py)
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_tutor_lessons():
    data = load_json(f"{DATA_DIR}/tutor_lessons_2102555.json")
    by_lesson = {}
    for item in data:
        lid = item["id"]
        if lid not in by_lesson:
            by_lesson[lid] = {
                "level": item.get("level"),
                "title": (item.get("title") or "").strip(),
                "desc": (item.get("desc") or "").strip(),
                "position": item.get("position"),
            }
        by_lesson[lid][item["type"]] = {"lms_id": item["lms_id"]}
    return by_lesson


def load_lms_results():
    data = load_json(f"{DATA_DIR}/lms_practice_result_2102555.csv.json")
    return {r["practice_id"]: r for r in data}


def load_lms_detail():
    detail = defaultdict(list)
    for path in sorted(glob.glob(f"{DATA_DIR}/lms_practice_result_detail_2102555*.json")):
        for row in load_json(path):
            detail[row["practice_id"]].append(row)
    return detail


def load_dt_sessions():
    data = load_json(f"{DATA_DIR}/vh_digital_teacher.learning_sessions_2102555_1.json")
    by_lesson = defaultdict(list)
    for s in data:
        eid = s.get("erpLessonId", "")
        if eid.isdigit():
            by_lesson[int(eid)].append(s)
    return by_lesson


def load_dt_results():
    data = load_json(f"{DATA_DIR}/vh_digital_teacher.learning_results_2102555_1.json")
    by_lesson = defaultdict(list)
    for r in data:
        eid = r.get("erpLessonId", "")
        if eid.isdigit():
            by_lesson[int(eid)].append(r)
    return by_lesson


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    for entity, char in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                          ("&gt;", ">"), ("&atilde;", "ã"), ("&aacute;", "á"),
                          ("&agrave;", "à"), ("&acirc;", "â"), ("&#160;", " ")]:
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def has_media(html: str) -> bool:
    return bool(re.search(r"<(img|audio|source)\b", html or "", re.IGNORECASE))


# ---------------------------------------------------------------------------
# In-class question extractors
# ---------------------------------------------------------------------------

def classify_audio(r):
    ad = (r.get("result") or {}).get("additionalData") or {}
    if "speaking" in ad:
        return "pronunciation_drill"
    if "warmup" in ad or "brainstorm" in ad:
        return "free_speaking"
    return "other"


def extract_pronunciation_drill(r):
    lms = r.get("lmsData") or {}
    return {
        "interaction_type": "pronunciation_drill",
        "expected_transcript": lms.get("expectedTranscript"),
        "question_prompt": lms.get("question"),
    }


def extract_free_speaking(r):
    lms = r.get("lmsData") or {}
    return {
        "interaction_type": "free_speaking",
        "question": lms.get("question"),
        "question_type": lms.get("questionType"),
    }


def extract_interactive(r):
    """Extract NON_AUDIO in-class exercise."""
    lms = r.get("lmsData") or {}
    qt = lms.get("questionType")
    question_text = lms.get("question") or ""
    raw_answers = lms.get("answers") or []

    if qt == "single_choice":
        options = [
            {"id": a.get("id"), "content": a.get("content"), "is_correct": a.get("isCorrect", False)}
            for a in raw_answers if isinstance(a, dict)
        ]
        correct_option = next((a["content"] for a in options if a["is_correct"]), None)
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "options": options,
            "correct_answer": correct_option,
        }

    elif qt == "true_false":
        correct_option = next(
            (a.get("content") for a in raw_answers if isinstance(a, dict) and a.get("isCorrect")),
            None,
        )
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "correct_answer": correct_option,
        }

    elif qt == "fill_paragraph":
        letter_pool = [a.get("content") for a in raw_answers if isinstance(a, dict)]
        correct_word = "".join(letter_pool)
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text,
            "letter_pool": letter_pool,
            "correct_answer": correct_word,
        }

    elif qt == "matching":
        terms = [a.get("content") for a in raw_answers if isinstance(a, dict)]
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text or "Match the following",
            "terms": terms,
        }

    else:
        return {
            "interaction_type": "interactive",
            "question_type": qt,
            "question": question_text or None,
            "requires_media": True,
        }


# ---------------------------------------------------------------------------
# Homework question extractor (full, all questions not just failed)
# ---------------------------------------------------------------------------

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
        if isinstance(answers, list) and answers and isinstance(answers[0], dict):
            correct_answer = str(answers[0].get("is_true") or answers[0].get("option") or "").strip() or None

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
                a for a in answers if isinstance(a, dict)
                and (a.get("is_true") is True
                     or str(a.get("is_true", "")).lower() == "true"
                     or (isinstance(a.get("is_true"), str)
                         and a["is_true"].upper() in ("A", "B", "TRUE", "ĐÚNG")))
            ]
            if correct_items:
                ca_text = strip_html(correct_items[0].get("content") or correct_items[0].get("content_text") or "")
                if has_media(correct_items[0].get("content", "")):
                    requires_media = True
                correct_answer = ca_text or None

    elif qt == "Xứng-Hợp":
        if isinstance(answers, dict):
            col1_texts = [strip_html(a.get("content", "")) for a in answers.get("column1", []) if isinstance(a, dict)]
            correct_answer = ", ".join(t for t in col1_texts if t) or None
            col2 = answers.get("column2", [])
            if any(has_media(a.get("content", "")) for a in col2 if isinstance(a, dict)):
                requires_media = True

    elif qt == "Kéo thả vào chỗ trống trong đoạn văn":
        if isinstance(answers, dict):
            correct_answer = strip_html(answers.get("correctAnswer", "")) or None
            col2 = answers.get("column2", [])
            pieces = [a.get("content_text") or strip_html(a.get("raw_content", "")) for a in col2 if isinstance(a, dict)]
            if pieces:
                question_text = (question_text or "Reorder") + ": " + " | ".join(p for p in pieces if p)

    return {
        "question_id": row.get("question_id"),
        "question_folder": row.get("question_folder"),
        "question_type": qt,
        "question_text": question_text[:300] if question_text else None,
        "requires_media": requires_media,
        "correct_answer": correct_answer,
    }


def build_homework_practice(lms_id, pr_by_pid, detail_by_pid):
    if not lms_id:
        return None
    r = pr_by_pid.get(lms_id)
    if not r:
        return None
    questions = [extract_lms_question(row) for row in detail_by_pid.get(lms_id, [])]
    return {
        "practice_id": lms_id,
        "score": r["diem_thi"],
        "correct": r["total_correct_question"],
        "total": r["total_question"],
        "submitted_date": (r.get("create_date") or "")[:10] or None,
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import os
    os.makedirs("output", exist_ok=True)

    print("Loading data...")
    tutor_by_lesson = load_tutor_lessons()
    pr_by_pid = load_lms_results()
    detail_by_pid = load_lms_detail()
    dt_sessions = load_dt_sessions()
    dt_results = load_dt_results()

    active_ids = set(tutor_by_lesson.keys()) | set(dt_sessions.keys())

    # Load program_lesson metadata for title/desc fallback
    program_meta = {}
    for path in sorted(glob.glob(f"{DATA_DIR}/program*lesson*.json")):
        raw = load_json(path)
        data_list = raw.get("data", raw) if isinstance(raw, dict) else raw
        for lesson in data_list:
            lid = lesson["id"]
            if lid not in program_meta:
                program_meta[lid] = {
                    "title": (lesson.get("title") or "").strip(),
                    "desc": (lesson.get("desc") or "").strip(),
                    "program_id": lesson.get("program_id"),
                }

    print(f"Processing {len(active_ids)} lessons...")

    lessons_export = []
    stats = {"lessons": 0, "pron_drills": 0, "free_speaking": 0,
             "interactive": 0, "lms_questions": 0}

    for lid in sorted(active_ids):
        tutor = tutor_by_lesson.get(lid, {})
        meta = program_meta.get(lid, {})

        title = meta.get("title") or tutor.get("title") or None
        desc = meta.get("desc") or tutor.get("desc") or None

        results = dt_results.get(lid, [])
        sessions = dt_sessions.get(lid, [])

        # Determine last activity date
        dates = []
        for s in sessions:
            d = s.get("startedAt")
            if isinstance(d, dict):
                dates.append(d.get("$date", "")[:10])
        bt_pid = (tutor.get("Bài tập") or {}).get("lms_id")
        lt_pid = (tutor.get("Luyện tập") or {}).get("lms_id")
        for pid in [bt_pid, lt_pid]:
            if pid and pid in pr_by_pid:
                d = pr_by_pid[pid].get("create_date", "")
                if d:
                    dates.append(d[:10])
        last_activity = max(dates) if dates else None

        # Skip lessons with no actual activity
        has_dt = bool(sessions)
        has_hw = bool(bt_pid and bt_pid in pr_by_pid) or bool(lt_pid and lt_pid in pr_by_pid)
        if not has_dt and not has_hw:
            continue

        # In-class: split by type
        audio = [r for r in results if r.get("interactionType") == "AUDIO"]
        non_audio = [r for r in results if r.get("interactionType") == "NON_AUDIO"]

        pron_drills = [extract_pronunciation_drill(r) for r in audio if classify_audio(r) == "pronunciation_drill"]
        free_sp = [extract_free_speaking(r) for r in audio if classify_audio(r) == "free_speaking"]
        interactive = [extract_interactive(r) for r in non_audio]

        # Homework
        bai_tap = build_homework_practice(bt_pid, pr_by_pid, detail_by_pid)
        luyen_tap = build_homework_practice(lt_pid, pr_by_pid, detail_by_pid)

        lessons_export.append({
            "lesson_id": lid,
            "program_id": meta.get("program_id"),
            "level": tutor.get("level"),
            "position": tutor.get("position"),
            "title": title,
            "desc": desc,
            "last_activity_date": last_activity,
            "in_class": {
                "session_count": len(sessions),
                "pronunciation_drills": pron_drills,
                "free_speaking": free_sp,
                "interactive": interactive,
            },
            "homework": {
                "bai_tap": bai_tap,
                "luyen_tap": luyen_tap,
            },
        })

        stats["lessons"] += 1
        stats["pron_drills"] += len(pron_drills)
        stats["free_speaking"] += len(free_sp)
        stats["interactive"] += len(interactive)
        stats["lms_questions"] += len(bai_tap["questions"] if bai_tap else [])
        stats["lms_questions"] += len(luyen_tap["questions"] if luyen_tap else [])

    # Sort by last_activity DESC
    lessons_export.sort(key=lambda l: l["last_activity_date"] or "0000", reverse=True)

    output = {
        "student_id": 2102555,
        "exported_at": str(TODAY),
        "total_lessons": len(lessons_export),
        "stats": stats,
        "lessons": lessons_export,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone → {OUTPUT_FILE}")
    print(f"Lessons:            {stats['lessons']}")
    print(f"Pronunciation drills: {stats['pron_drills']}")
    print(f"Free speaking:       {stats['free_speaking']}")
    print(f"Interactive (NON_AUDIO): {stats['interactive']}")
    print(f"LMS homework questions:  {stats['lms_questions']}")


if __name__ == "__main__":
    main()
