"""
Export all questions (in-class + homework) for each lesson the student has studied.

Output: output/questions_export.json

Structure per lesson:
  in_class:
    pronunciation_drills[]  - scripted phonetic exercises (expectedTranscript + student result)
    free_speaking[]         - open-ended speaking (question + transcript + score + answer_type)
    interactive[]           - NON_AUDIO exercises (single_choice, true_false, fill_paragraph, matching)
  homework:
    bai_tap{} / luyen_tap{}  - lms_id + metadata from `data/<id>/tutor_lesson*.json` (Bài tập / Luyện tập),
    full `questions[]`        - prefer lms_practice_result_detail; if missing, fall back to
    `data/practice_question_bank.json` by practice_id (same lms_id), so all lesson questions
    are included even when the student has not attempted the practice.
"""

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import preprocess

# Set by main() before any loader is called
DATA_DIR = "data"
STUDENT_ID = "2102555"
OUTPUT_FILE = "output/questions_export.json"
TODAY = date(2026, 4, 21)
QUESTION_BANK_FILES = [
    "data/practice_question_bank.json",
    "practice_question_bank.json",
]


# ---------------------------------------------------------------------------
# Global practice → questions (LMS catalogue; not student-specific)
# ---------------------------------------------------------------------------


def _question_bank_path(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    repo = Path(__file__).resolve().parent
    for rel in QUESTION_BANK_FILES:
        p = (repo / rel).resolve()
        if p.is_file():
            return p
    return None


def load_practice_question_bank(path: str | None = None) -> dict:
    """
    practice_id (lms) -> [ rows compatible with extract_lms_question: content, answers, ... ]
    """
    p = _question_bank_path(path)
    if p is None:
        return {}
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return {}
    by_pid: dict = defaultdict(list)
    for row in data:
        if not isinstance(row, dict):
            continue
        pid = row.get("practice_id")
        if pid is not None:
            by_pid[pid].append(row)
    for pid, rows in by_pid.items():
        rows.sort(key=lambda x: (x.get("question_id") or 0, x.get("id") or 0))
    return dict(by_pid)


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
        "question_text": question_text or None,
        "requires_media": requires_media,
        "correct_answer": correct_answer,
    }


def _detail_rows_for_practice(lms_id, detail_by_pid):
    rows = list(detail_by_pid.get(lms_id) or [])
    rows.sort(key=lambda x: (x.get("question_id") or 0, x.get("id") or 0))
    return rows


def build_homework_practice(
    lms_id, pr_by_pid, detail_by_pid, section_meta=None, bank_by_pid=None,
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
    # Prefer scored total, else row count, else catalogue size from tutor
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global DATA_DIR, STUDENT_ID, OUTPUT_FILE

    import argparse
    import os

    parser = argparse.ArgumentParser(description="Export questions for student learning data.")
    parser.add_argument(
        "student_id", nargs="?", type=str, default="2102555",
        help="Student data folder under data/ (e.g. 2102555 or 2111414_newstudent). Default: 2102555",
    )
    parser.add_argument(
        "--question-bank", metavar="PATH", default=None,
        help="LMS question catalogue (JSON array, practice_id = lms). "
        "Default: data/practice_question_bank.json if present.",
    )
    args = parser.parse_args()

    STUDENT_ID = str(args.student_id).strip()
    DATA_DIR = f"data/{STUDENT_ID}"
    OUTPUT_FILE = f"output/{STUDENT_ID}/questions_export.json"

    os.makedirs(f"output/{STUDENT_ID}", exist_ok=True)

    print("Loading data...")
    bank_by_pid = load_practice_question_bank(args.question_bank)
    qbank_path = _question_bank_path(args.question_bank)
    if qbank_path:
        print(f"  Question bank: {qbank_path} ({len(bank_by_pid)} practice ids)")
    else:
        print("  Question bank: not found — add data/practice_question_bank.json to backfill "
              "full questions when LMS practice detail is missing")

    preprocess.DATA_DIR = DATA_DIR
    tutor_by_lesson, _lms_to_lesson = preprocess.load_tutor_lessons()
    pr_by_pid = preprocess.load_lms_practice_results()
    detail_by_pid = preprocess.load_lms_detail()
    dt_sessions = preprocess.load_dt_sessions()
    dt_results = preprocess.load_dt_results()

    active_ids = set(tutor_by_lesson.keys()) | set(dt_sessions.keys())

    print(f"Processing {len(active_ids)} lessons...")

    lessons_export = []
    stats = {"lessons": 0, "pron_drills": 0, "free_speaking": 0,
             "interactive": 0, "lms_questions": 0}

    for lid in sorted(active_ids):
        tutor = tutor_by_lesson.get(lid, {})

        title = tutor.get("title") or None
        desc = tutor.get("desc") or None

        results = dt_results.get(lid, [])
        sessions = dt_sessions.get(lid, [])

        # Determine last activity date
        dates = []
        for s in sessions:
            d = s.get("startedAt")
            if isinstance(d, dict):
                dates.append(d.get("$date", "")[:10])
        bai_tap_meta = tutor.get("Bài tập") or {}
        luyen_tap_meta = tutor.get("Luyện tập") or {}
        bt_pid = bai_tap_meta.get("lms_id")
        lt_pid = luyen_tap_meta.get("lms_id")
        for pid in [bt_pid, lt_pid]:
            if not pid:
                continue
            if pid in pr_by_pid:
                d = pr_by_pid[pid].get("create_date", "")
                if d:
                    dates.append(d[:10])
            for row in detail_by_pid.get(pid) or []:
                d = row.get("create_date") or row.get("update_date")
                if isinstance(d, str) and d:
                    dates.append(d[:10])
        last_activity = max(dates) if dates else None

        def _has_lms_content(pid):
            """LMS data from this student only (not the global question bank — bank backfills
            questions in build_homework_practice but must not add lessons with no real activity)."""
            if not pid:
                return False
            return pid in pr_by_pid or bool(detail_by_pid.get(pid))

        # Skip lessons with no actual activity
        has_dt = bool(sessions)
        has_hw = _has_lms_content(bt_pid) or _has_lms_content(lt_pid)
        if not has_dt and not has_hw:
            continue

        # In-class: split by type
        audio = [r for r in results if r.get("interactionType") == "AUDIO"]
        non_audio = [r for r in results if r.get("interactionType") == "NON_AUDIO"]

        pron_drills = [extract_pronunciation_drill(r) for r in audio if classify_audio(r) == "pronunciation_drill"]
        free_sp = [extract_free_speaking(r) for r in audio if classify_audio(r) == "free_speaking"]
        interactive = [extract_interactive(r) for r in non_audio]

        # Homework
        bai_tap = build_homework_practice(
            bt_pid, pr_by_pid, detail_by_pid, bai_tap_meta, bank_by_pid=bank_by_pid,
        )
        luyen_tap = build_homework_practice(
            lt_pid, pr_by_pid, detail_by_pid, luyen_tap_meta, bank_by_pid=bank_by_pid,
        )

        lessons_export.append({
            "lesson_id": lid,
            "program_id": None,
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

    stats["question_bank_practice_ids"] = len(bank_by_pid)
    stats["question_bank_path"] = str(qbank_path) if qbank_path else None

    output = {
        "student_id": STUDENT_ID,
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
    print(f"Question bank (practice ids): {stats['question_bank_practice_ids']}")


if __name__ == "__main__":
    main()
