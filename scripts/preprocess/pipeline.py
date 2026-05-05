import json
from collections import defaultdict
from datetime import date

from . import config
from .digital_teacher import (
    build_dt_in_class,
    compute_weakness_score,
    derive_status,
    latest_activity_date,
)
from .lms_questions import build_lms_homework
from .loaders import (
    load_dt_results,
    load_dt_sessions,
    load_lms_detail,
    load_lms_practice_results,
    load_question_bank,
    load_tutor_lessons,
)
from .scoring import forgetting_score


def build_student_context():
    print("Loading data files...")
    tutor_by_lesson, _ = load_tutor_lessons()
    pr_by_pid = load_lms_practice_results()
    detail_by_pid = load_lms_detail()
    dt_sessions = load_dt_sessions()
    dt_results = load_dt_results()
    question_bank_by_pid = load_question_bank()

    active_lesson_ids = set(tutor_by_lesson.keys()) | set(dt_sessions.keys())
    print(f"Processing {len(active_lesson_ids)} student-active lessons")

    records = []
    for lid in sorted(active_lesson_ids):
        tutor_entry = tutor_by_lesson.get(lid, {})

        in_class = build_dt_in_class(dt_sessions.get(lid, []), dt_results.get(lid, []))
        homework = build_lms_homework(tutor_entry, pr_by_pid, detail_by_pid, {}, question_bank_by_pid)
        status = derive_status(in_class, homework)

        last_date_str = latest_activity_date(
            in_class.get("latest_session_date"),
            (homework.get("bai_tap") or {}).get("submitted_date"),
            (homework.get("luyen_tap") or {}).get("submitted_date"),
        )

        days_since = None
        f_score = None
        w_score = None
        composite = None
        if last_date_str:
            days_since = (config.TODAY - date.fromisoformat(last_date_str)).days
            f_score = forgetting_score(days_since)
            w_score = compute_weakness_score(homework, in_class)
            composite = round(0.5 * f_score + 0.5 * w_score, 4)

        records.append(
            {
                "lesson_id": lid,
                "program_id": None,
                "level": tutor_entry.get("level"),
                "position": tutor_entry.get("position"),
                "title": tutor_entry.get("title") or None,
                "desc": tutor_entry.get("desc") or None,
                "status": status,
                "last_activity_date": last_date_str,
                "days_since_last_practice": days_since,
                "forgetting_score": f_score,
                "weakness_score": w_score,
                "composite_priority_score": composite,
                "in_class": in_class,
                "homework": homework,
            }
        )

    records = [r for r in records if r["status"] != "not_started"]

    records.sort(
        key=lambda r: (r["composite_priority_score"] or 0, r["days_since_last_practice"] or 0),
        reverse=True,
    )
    return records


def build_scored_candidates(records):
    """
    Pre-ranked candidate list for Agent 2 (assignment agent).
    Exposes the actual question content (not links) for each failed question,
    so the agent can present exercises directly to the student.

    Includes both:
      - attempted lessons: failed questions from detail records
      - not_attempted (in_class_only) lessons: question preview from practice_question_bank
        tagged with status="not_attempted" so the agent knows homework is pending
    """
    candidates = []
    for r in records:
        if r["status"] not in ("completed", "homework_only", "in_class_only"):
            continue
        hw = r["homework"]
        bt = hw.get("bai_tap") or {}
        lt = hw.get("luyen_tap") or {}
        lms_ids = hw.get("lms_ids", {})

        homework_status = "attempted" if hw.get("attempted") else "not_attempted"

        if hw.get("attempted"):
            all_failed = hw.get("worst_questions", [])
            text_questions = [q for q in all_failed if not q.get("requires_media")]
            media_questions = [q for q in all_failed if q.get("requires_media")]
            question_bank_preview = []
        else:
            all_failed = []
            text_questions = []
            media_questions = []
            preview = hw.get("not_attempted_preview", {})
            question_bank_preview = []
            for section_qs in preview.values():
                question_bank_preview.extend(section_qs)
            question_bank_preview = question_bank_preview[: config.WORST_LMS_Q_LIMIT]

            if not lms_ids.get("bai_tap") and not lms_ids.get("luyen_tap"):
                continue

        candidates.append(
            {
                "lesson_id": r["lesson_id"],
                "title": r["title"],
                "level": r["level"],
                "last_activity_date": r.get("last_activity_date"),
                "days_since_last_practice": r["days_since_last_practice"],
                "forgetting_score": r["forgetting_score"],
                "weakness_score": r["weakness_score"],
                "composite_priority_score": r["composite_priority_score"],
                "homework_status": homework_status,
                "weak_skills": hw.get("weak_skills", []),
                "failed_text_questions": text_questions,
                "question_bank_preview": question_bank_preview,
                "failed_media_questions_count": len(media_questions),
                "worst_speaking_items": r["in_class"].get("worst_speaking_items", []),
                "practice_ids": {
                    "bai_tap": bt.get("practice_id") or lms_ids.get("bai_tap"),
                    "luyen_tap": lt.get("practice_id") or lms_ids.get("luyen_tap"),
                },
            }
        )

    candidates = [
        c
        for c in candidates
        if (
            c.get("failed_text_questions")
            or c.get("question_bank_preview")
            or c.get("worst_speaking_items")
            or c.get("failed_media_questions_count", 0) > 0
        )
    ]
    above = [c for c in candidates if (c["composite_priority_score"] or 0) >= config.MIN_CANDIDATE_SCORE]
    below = [c for c in candidates if (c["composite_priority_score"] or 0) < config.MIN_CANDIDATE_SCORE]
    pool = (
        above
        if len(above) >= config.MIN_CANDIDATE_POOL_FALLBACK
        else above + below[: config.MIN_CANDIDATE_POOL_FALLBACK - len(above)]
    )
    return pool[: config.MAX_CANDIDATE_POOL_SIZE]


def build_summary(records):
    total = len(records)
    by_status = defaultdict(int)
    for r in records:
        by_status[r["status"]] += 1

    skill_totals = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in records:
        for folder, s in r["homework"].get("skill_breakdown", {}).items():
            skill_totals[folder]["correct"] += s["correct"]
            skill_totals[folder]["total"] += s["total"]

    overall_skill = {
        folder: {
            "correct": c["correct"],
            "total": c["total"],
            "accuracy": round(c["correct"] / c["total"], 3) if c["total"] else None,
        }
        for folder, c in skill_totals.items()
    }
    weak_skills_global = [
        f for f, s in overall_skill.items() if s["accuracy"] is not None and s["accuracy"] < 0.70
    ]

    all_pron_scores, all_free_scores, all_brain_scores, all_convo_scores = [], [], [], []
    all_answer_types = defaultdict(int)
    all_brain_answer_types = defaultdict(int)
    for r in records:
        ic = r.get("in_class", {})
        pron_avg = ic.get("pronunciation_score_avg")
        pron_n = ic.get("pronunciation_attempts", 0)
        free_avg = ic.get("free_speaking_score_avg")
        free_n = ic.get("free_speaking_attempts", 0)
        br_avg = ic.get("brainstorm_score_avg")
        br_n = ic.get("brainstorm_attempts", 0)
        convo_avg = ic.get("conversation_score_avg")
        convo_n = ic.get("conversation_attempts", 0)
        if pron_avg is not None and pron_n > 0:
            all_pron_scores.extend([pron_avg] * pron_n)
        if free_avg is not None and free_n > 0:
            all_free_scores.extend([free_avg] * free_n)
        if br_avg is not None and br_n > 0:
            all_brain_scores.extend([br_avg] * br_n)
        if convo_avg is not None and convo_n > 0:
            all_convo_scores.extend([convo_avg] * convo_n)
        for at, cnt in ic.get("free_speaking_answer_type_dist", {}).items():
            all_answer_types[at] += cnt
        for at, cnt in ic.get("brainstorm_answer_type_dist", {}).items():
            all_brain_answer_types[at] += cnt

    brain_avg = round(sum(all_brain_scores) / len(all_brain_scores), 2) if all_brain_scores else None
    free_avg = round(sum(all_free_scores) / len(all_free_scores), 2) if all_free_scores else None
    pron_avg = round(sum(all_pron_scores) / len(all_pron_scores), 2) if all_pron_scores else None
    convo_avg = round(sum(all_convo_scores) / len(all_convo_scores), 2) if all_convo_scores else None

    critical_speaking = []
    if brain_avg is not None and brain_avg < 30:
        critical_speaking.append("brainstorm")
    if free_avg is not None and free_avg < 50:
        critical_speaking.append("free_speaking")

    return {
        "student_id": config.STUDENT_ID,
        "reference_date": str(config.TODAY),
        "total_lessons": total,
        "lessons_by_status": dict(by_status),
        "overall_homework_skill_breakdown": overall_skill,
        "weak_skills_global": weak_skills_global,
        "critical_speaking_types": critical_speaking,
        "stability_days": config.EBBINGHAUS_STABILITY_DAYS,
        "overall_pronunciation_score_avg": pron_avg,
        "overall_free_speaking_score_avg": free_avg,
        "overall_brainstorm_score_avg": brain_avg,
        "overall_conversation_score_avg": convo_avg,
        "overall_free_speaking_answer_type_dist": dict(all_answer_types),
        "overall_brainstorm_answer_type_dist": dict(all_brain_answer_types),
        "forgetting_curve_note": (
            f"All lessons have 1 prior attempt. Stability set to {config.EBBINGHAUS_STABILITY_DAYS:.0f} days. "
            "Lessons older than ~21 days score >0.95 (mostly forgotten). "
            "Agent should prioritise by composite_priority_score."
        ),
    }


def main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Preprocess student learning data.")
    parser.add_argument(
        "student_id",
        nargs="?",
        type=str,
        default="2102555",
        help="Student data folder under data/ (e.g. 2102555 or 2111414_newstudent). Default: 2102555",
    )
    args = parser.parse_args()

    config.STUDENT_ID = str(args.student_id).strip()
    config.DATA_DIR = f"data/{config.STUDENT_ID}"
    config.OUTPUT_FILE = f"output/{config.STUDENT_ID}/student_context.json"

    os.makedirs(f"output/{config.STUDENT_ID}", exist_ok=True)

    records = build_student_context()
    summary = build_summary(records)
    scored_candidates = build_scored_candidates(records)

    output = {
        "summary": summary,
        "scored_candidates": scored_candidates,
        "lessons": records,
    }

    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(records)} lessons → {config.OUTPUT_FILE}")
    print(f"Status: {summary['lessons_by_status']}")
    print(f"Scored candidates (Agent 2 pool): {len(scored_candidates)}")
    print(f"Pronunciation avg: {summary['overall_pronunciation_score_avg']}")
    print(f"Free speaking (warmup) avg: {summary['overall_free_speaking_score_avg']}")
    print(f"Brainstorm (ảnh→từ) avg:     {summary['overall_brainstorm_score_avg']}")
    print(f"Conversation avg:  {summary['overall_conversation_score_avg']}")
    print(f"Global weak skills: {summary['weak_skills_global']}")
    print("\nTop 5 priority lessons for re-practice:")
    for r in [c for c in scored_candidates if c["composite_priority_score"]][:5]:
        print(
            f"  [{r['composite_priority_score']:.3f}] lesson {r['lesson_id']} "
            f"'{(r['title'] or '')[:45]}' "
            f"| forget={r['forgetting_score']:.3f} weak={r['weakness_score']:.3f} "
            f"| {r['days_since_last_practice']}d ago"
        )
