import argparse
import json
import os

from .. import preprocess
from . import config
from .bank import _question_bank_path, load_practice_question_bank
from .homework import build_homework_practice
from .in_class import (
    compute_session_metrics,
    extract_brainstorm,
    extract_conversation,
    extract_free_speaking,
    extract_interactive,
    extract_pronunciation_drill,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export questions for student learning data.")
    parser.add_argument(
        "student_id",
        nargs="?",
        type=str,
        default="2102555",
        help="Student data folder under data/ (e.g. 2102555 or 2111414_newstudent). Default: 2102555",
    )
    parser.add_argument(
        "--question-bank",
        metavar="PATH",
        default=None,
        help="LMS question catalogue (JSON array, practice_id = lms). "
        "Default: data/practice_question_bank.json if present.",
    )
    args = parser.parse_args()

    config.STUDENT_ID = str(args.student_id).strip()
    config.DATA_DIR = f"data/{config.STUDENT_ID}"
    config.OUTPUT_FILE = f"output/{config.STUDENT_ID}/questions_export.json"

    os.makedirs(f"output/{config.STUDENT_ID}", exist_ok=True)

    print("Loading data...")
    bank_by_pid = load_practice_question_bank(args.question_bank)
    qbank_path = _question_bank_path(args.question_bank)
    if qbank_path:
        print(f"  Question bank: {qbank_path} ({len(bank_by_pid)} practice ids)")
    else:
        print(
            "  Question bank: not found — add data/practice_question_bank.json to backfill "
            "full questions when LMS practice detail is missing"
        )

    preprocess.config.DATA_DIR = config.DATA_DIR
    tutor_by_lesson, _lms_to_lesson = preprocess.load_tutor_lessons()
    pr_by_pid = preprocess.load_lms_practice_results()
    detail_by_pid = preprocess.load_lms_detail()
    dt_sessions = preprocess.load_dt_sessions()
    dt_results = preprocess.load_dt_results()

    active_ids = set(tutor_by_lesson.keys()) | set(dt_sessions.keys())

    print(f"Processing {len(active_ids)} lessons...")

    lessons_export = []
    stats = {
        "lessons": 0,
        "pron_drills": 0,
        "free_speaking": 0,
        "brainstorm": 0,
        "conversation": 0,
        "interactive": 0,
        "lms_questions": 0,
    }

    for lid in sorted(active_ids):
        tutor = tutor_by_lesson.get(lid, {})

        title = tutor.get("title") or None
        desc = tutor.get("desc") or None

        results = dt_results.get(lid, [])
        sessions = dt_sessions.get(lid, [])

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
            if not pid:
                return False
            return pid in pr_by_pid or bool(detail_by_pid.get(pid))

        has_dt = bool(sessions)
        has_hw = _has_lms_content(bt_pid) or _has_lms_content(lt_pid)
        if not has_dt and not has_hw:
            continue

        audio = [r for r in results if r.get("interactionType") == "AUDIO"]
        non_audio = [r for r in results if r.get("interactionType") == "NON_AUDIO"]

        pron_drills = [
            extract_pronunciation_drill(r)
            for r in audio
            if preprocess.classify_audio(r) == "pronunciation_drill"
        ]
        free_sp = [
            extract_free_speaking(r) for r in audio if preprocess.classify_audio(r) == "free_speaking"
        ]
        brainstorm_sp = [
            extract_brainstorm(r) for r in audio if preprocess.classify_audio(r) == "brainstorm"
        ]
        convos = [
            extract_conversation(r) for r in audio if preprocess.classify_audio(r) == "conversation"
        ]
        interactive = [extract_interactive(r) for r in non_audio]

        bai_tap = build_homework_practice(
            bt_pid, pr_by_pid, detail_by_pid, bai_tap_meta, bank_by_pid=bank_by_pid
        )
        luyen_tap = build_homework_practice(
            lt_pid, pr_by_pid, detail_by_pid, luyen_tap_meta, bank_by_pid=bank_by_pid
        )

        session_metrics = compute_session_metrics(sessions, results)

        lessons_export.append(
            {
                "lesson_id": lid,
                "program_id": None,
                "level": tutor.get("level"),
                "position": tutor.get("position"),
                "title": title,
                "desc": desc,
                "last_activity_date": last_activity,
                "in_class": {
                    "session_count": len(sessions),
                    "session_metrics": session_metrics,
                    "pronunciation_drills": pron_drills,
                    "free_speaking": free_sp,
                    "brainstorm": brainstorm_sp,
                    "conversation": convos,
                    "interactive": interactive,
                },
                "homework": {
                    "bai_tap": bai_tap,
                    "luyen_tap": luyen_tap,
                },
            }
        )

        stats["lessons"] += 1
        stats["pron_drills"] += len(pron_drills)
        stats["free_speaking"] += len(free_sp)
        stats["brainstorm"] += len(brainstorm_sp)
        stats["conversation"] += len(convos)
        stats["interactive"] += len(interactive)
        stats["lms_questions"] += len(bai_tap["questions"] if bai_tap else [])
        stats["lms_questions"] += len(luyen_tap["questions"] if luyen_tap else [])

    lessons_export.sort(key=lambda l: l["last_activity_date"] or "0000", reverse=True)

    stats["question_bank_practice_ids"] = len(bank_by_pid)
    stats["question_bank_path"] = str(qbank_path) if qbank_path else None

    output = {
        "student_id": config.STUDENT_ID,
        "exported_at": str(config.TODAY),
        "total_lessons": len(lessons_export),
        "stats": stats,
        "lessons": lessons_export,
    }

    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone → {config.OUTPUT_FILE}")
    print(f"Lessons:            {stats['lessons']}")
    print(f"Pronunciation drills: {stats['pron_drills']}")
    print(f"Free speaking (warmup): {stats['free_speaking']}")
    print(f"Brainstorm (ảnh→từ):  {stats['brainstorm']}")
    print(f"Conversation:         {stats['conversation']}")
    print(f"Interactive (NON_AUDIO): {stats['interactive']}")
    print(f"LMS homework questions:  {stats['lms_questions']}")
    print(f"Question bank (practice ids): {stats['question_bank_practice_ids']}")
