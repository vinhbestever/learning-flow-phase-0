"""
Preprocess raw learning data for a given student.

Usage:
    python preprocess.py [student_folder]   (default: 2102555)

    student_folder is the directory name under data/ (numeric or e.g. 2111414_newstudent).

Output: output/{student_id}/student_context.json

Designed for a two-agent pipeline:
  Agent 1 (Analysis)  — reads full context, produces weakness analysis
  Agent 2 (Assignment)— reads analysis + scored_candidates, selects 10-15 exercises

Key features:
  - link_practice URL per bai_tap / luyen_tap (agent can generate assignment links)
  - days_since_last_practice + forgetting_score per lesson (Ebbinghaus, no prior reps)
  - weakness_score per lesson (composite of homework + free speaking)
  - composite_priority_score = 0.5 * forgetting + 0.5 * weakness
  - scored_candidates list (top lessons pre-ranked for Agent 2)
  - worst_lms_questions per lesson (question-level failures from detail records)
  - AUDIO subtypes separated: pronunciation_drill, brainstorm (ảnh + từ mục tiêu), free_speaking (warmup / nói mở), conversation
  - in_class.session_metrics: cups, audio_turns, reaction times (latest DT session)

Supports tutor_lesson export variants:
  - 2102555 style: 'type' field = "Bài tập"/"Luyện tập", 'id' = lesson_id
  - 2102553 style: 'title' = section type, 'class_lesson_id' = lesson_id (erpLessonId)
  - English label: 'type' ending in "Homework" (e.g. "Unit 1A - Lesson 1 - Homework") → treated as Bài tập
"""

import glob
import json
import math
from collections import defaultdict
from datetime import date

from lms_question_rich import rich_question_fields

# Set by main() before any loader is called
DATA_DIR = "data"
STUDENT_ID = "2102555"
OUTPUT_FILE = "output/student_context.json"

TODAY = date(2026, 4, 21)           # injected reference date
EBBINGHAUS_STABILITY_DAYS = 1.0     # default stability for first exposure (no repetitions)
WORST_SPEAKING_LIMIT = 5
WORST_LMS_Q_LIMIT = 5
MAX_CANDIDATE_POOL_SIZE = 40        # hard ceiling for Agent 2 context
MIN_CANDIDATE_SCORE = 0.50          # minimum composite_priority_score to enter the pool
MIN_CANDIDATE_POOL_FALLBACK = 5     # guarantee at least this many if not enough above threshold
QUESTION_BANK_PATH = "data/practice_question_bank.json"
QUESTION_BANK_PREVIEW_LIMIT = 5    # max questions per section shown from bank for not-attempted

SECTION_TYPE_MAP = {
    "Bài tập": "Bài tập",
    "Luyện tập": "Luyện tập",
    "Bài luyện tập": "Luyện tập",  # alias used in some exports
}


def _normalize_tutor_section_type(raw: str) -> str:
    """Map export-specific labels onto Bài tập / Luyện tập for downstream logic."""
    s = (raw or "").strip()
    if not s:
        return s
    mapped = SECTION_TYPE_MAP.get(s, s)
    if mapped in ("Bài tập", "Luyện tập"):
        return mapped
    low = s.lower()
    if low.endswith("homework") or " - homework" in low:
        return "Bài tập"
    if "luyện tập" in low or low.endswith("practice"):
        return "Luyện tập"
    return mapped


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_tutor_lessons():
    """
    Returns:
      by_lesson: lesson_id -> {level, title, desc, position, "Bài tập": {...}, "Luyện tập": {...}}
      lms_to_lesson: lms_id -> (lesson_id, section_type)

    Handles export formats:
      - 'type' field present: lesson_id = item['id'], section_type normalized from item['type']
      - 'type' field absent:  lesson_id = item['class_lesson_id'], section_type from item['title']
    """
    paths = sorted(glob.glob(f"{DATA_DIR}/tutor_lesson*.json"))
    if not paths:
        return {}, {}

    all_items = []
    for path in paths:
        all_items.extend(load_json(path))

    # Detect format: 2102555 has truthy 'type'; 2102553 has None/missing 'type'
    has_type_field = any(item.get("type") for item in all_items)

    by_lesson = {}
    lms_to_lesson = {}

    for item in all_items:
        if has_type_field:
            lid = item["id"]
            section_type = _normalize_tutor_section_type(item.get("type", ""))
            lesson_title = (item.get("title") or "").strip()
            lesson_desc = (item.get("desc") or "").strip()
        else:
            lid = item["class_lesson_id"]
            section_type = _normalize_tutor_section_type(item.get("title", ""))
            lesson_title = ""  # title holds section type in this format
            lesson_desc = (item.get("desc") or "").strip()

        lms_id = item.get("lms_id")

        if lid not in by_lesson:
            by_lesson[lid] = {
                "level": item.get("level"),
                "title": lesson_title,
                "desc": lesson_desc,
                "position": item.get("position"),
            }
        if section_type in ("Bài tập", "Luyện tập"):
            by_lesson[lid][section_type] = {
                "lms_id": lms_id,
                "lms_num_question": item.get("lms_num_question", 0),
                "completed_lesson": item.get("completed_lesson", 0),
            }
        if lms_id:
            lms_to_lesson[lms_id] = (lid, section_type)

    return by_lesson, lms_to_lesson


def load_lms_practice_results():
    """Returns dict: practice_id -> result record."""
    results = {}
    for path in sorted(glob.glob(f"{DATA_DIR}/lms_practice_result*.json")):
        if "detail" in path:
            continue
        for r in load_json(path):
            results[r["practice_id"]] = r
    return results


def load_lms_detail():
    """Returns dict: practice_id -> [detail_row, ...]."""
    detail = defaultdict(list)
    for path in sorted(glob.glob(f"{DATA_DIR}/lms_practice_result_detail*.json")):
        for row in load_json(path):
            detail[row["practice_id"]].append(row)
    return detail


def load_dt_sessions():
    """Returns dict: lesson_id (int) -> [session, ...]."""
    by_lesson = defaultdict(list)
    for path in sorted(glob.glob(f"{DATA_DIR}/vh_digital_teacher.learning_sessions*.json")):
        for s in load_json(path):
            eid = s.get("erpLessonId", "")
            if str(eid).isdigit():
                by_lesson[int(eid)].append(s)
    return by_lesson


def load_dt_results():
    """Returns dict: lesson_id (int) -> [result, ...]."""
    by_lesson = defaultdict(list)
    for path in sorted(glob.glob(f"{DATA_DIR}/vh_digital_teacher.learning_results*.json")):
        for r in load_json(path):
            eid = r.get("erpLessonId", "")
            if str(eid).isdigit():
                by_lesson[int(eid)].append(r)
    return by_lesson


def load_question_bank():
    """
    Returns dict: practice_id -> [question_record, ...].
    Reads from the global practice_question_bank.json (not per-student).
    """
    try:
        items = load_json(QUESTION_BANK_PATH)
    except (FileNotFoundError, IOError):
        return {}
    bank = defaultdict(list)
    for q in items:
        pid = q.get("practice_id")
        if pid is not None:
            bank[pid].append(q)
    return dict(bank)


# ---------------------------------------------------------------------------
# Transform helpers
# ---------------------------------------------------------------------------

def parse_mongo_date(value):
    if isinstance(value, dict):
        return value.get("$date", "")
    return str(value) if value else ""


def iso_to_date(iso_str):
    return iso_str[:10] if iso_str else None


def classify_audio(result_record):
    """
    conversation:        lmsType == "conversation"  (structured dialogue, grammar+pron scoring)
    pronunciation_drill: additionalData.speaking    (phonetic accuracy drills)
    brainstorm:          additionalData.brainstorm (nhìn ảnh / gợi ý, nói các từ mục tiêu)
    free_speaking:       additionalData.warmup only (nói mở / icebreaker, không phải brainstorm)
    other:               no recognised lmsType or additionalData
    """
    if result_record.get("lmsType") == "conversation":
        return "conversation"
    ad = (result_record.get("result") or {}).get("additionalData") or {}
    if "speaking" in ad:
        return "pronunciation_drill"
    if "brainstorm" in ad:
        return "brainstorm"
    if "warmup" in ad:
        return "free_speaking"
    return "other"


def extract_user_answer_type(additional_data):
    if not isinstance(additional_data, dict):
        return None
    for v in additional_data.values():
        if isinstance(v, dict):
            uat = (v.get("result") or {}).get("userAnswerType")
            if uat:
                return uat
    return None


# ---------------------------------------------------------------------------
# Forgetting curve (Ebbinghaus, no repetition data)
# ---------------------------------------------------------------------------

def forgetting_score(days_since: int, stability: float = EBBINGHAUS_STABILITY_DAYS) -> float:
    """
    Proportion of memory forgotten: 1 - e^(-t/S).
    With a single prior exposure and default stability ≈1 day, anything
    older than ~7 days scores ≥ 0.999 (effectively fully forgotten).
    Returns 0.0–1.0; higher = more forgotten.
    """
    if days_since <= 0:
        return 0.0
    return round(1.0 - math.exp(-days_since / stability), 4)


def retention_score(days_since: int, stability: float = EBBINGHAUS_STABILITY_DAYS) -> float:
    """Complement of forgetting_score. 1.0 = fully retained."""
    return round(1.0 - forgetting_score(days_since, stability), 4)


# ---------------------------------------------------------------------------
# Per-lesson builders
# ---------------------------------------------------------------------------

import re as _re

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

    # Detect media dependency in question content
    requires_media = _has_media(raw_content)

    # Parse answers JSON
    try:
        answers = json.loads(raw_answers)
    except Exception:
        answers = []

    # Parse student submission
    try:
        bai_lam = json.loads(raw_bai_lam)
        student_items = [item for item in bai_lam if isinstance(item, dict)]
    except Exception:
        student_items = []

    correct_answer = None
    student_ans = None

    if qt == "Điền vào chỗ trống":
        # Each answers[i] is one blank; bai_lam[i].u is student's typed text.
        # is_true holds the canonical correct value; option is a fallback.
        if isinstance(answers, list):
            correct_parts = [
                str(a.get("is_true") or a.get("option") or "").strip()
                for a in answers if isinstance(a, dict)
            ]
            correct_answer = " / ".join(p for p in correct_parts if p) or None
            student_parts = [item.get("u") or "" for item in student_items[:len(answers)]]
            student_ans = " / ".join(p for p in student_parts if p) or None

    elif qt == "Trả lời bằng giọng nói":
        # answers: ["correct text"] or [{"content": "correct text", "is_true": True}]
        if isinstance(answers, list) and answers:
            a0 = answers[0]
            if isinstance(a0, str):
                correct_answer = a0.strip() or None
            elif isinstance(a0, dict):
                correct_answer = _strip_html(
                    a0.get("content") or a0.get("content_text") or ""
                ) or None
                requires_media = requires_media or _has_media(a0.get("content", ""))
        student_ans = student_items[0].get("u") if student_items else None

    elif qt in ("Một lựa chọn", "Nhiều lựa chọn"):
        # bai_lam: [{u:"1"|"0", is_correct:...}, ...] — u="1" means student selected that option
        if isinstance(answers, list):
            correct_items = [
                a for a in answers
                if isinstance(a, dict) and (
                    a.get("is_true") is True
                    or str(a.get("is_true", "")).lower() == "true"
                    or (isinstance(a.get("is_true"), str) and a["is_true"].upper() in ("A", "B", "TRUE", "ĐÚNG"))
                )
            ]
            if correct_items:
                ca = correct_items[0]
                ca_text = _strip_html(ca.get("content") or ca.get("content_text") or "")
                if _has_media(ca.get("content", "")):
                    requires_media = True
                correct_answer = ca_text or None

            # Map selection flags (u="1") back to actual answer text
            selected_texts = []
            for i, item in enumerate(student_items):
                if item.get("u") == "1" and i < len(answers):
                    a = answers[i]
                    if isinstance(a, dict):
                        txt = _strip_html(a.get("content") or a.get("content_text") or "")
                        if _has_media(a.get("content", "")):
                            requires_media = True
                        selected_texts.append(txt or f"option_{i+1}")
                    elif isinstance(a, str):
                        selected_texts.append(a)
            student_ans = selected_texts[0] if (qt == "Một lựa chọn" and selected_texts) else (selected_texts or None)

    elif qt == "Xứng-Hợp":
        # bai_lam: [{u: col2_index (1-based), is_correct:...}, ...] per col1 item
        if isinstance(answers, dict):
            col1 = answers.get("column1", [])
            col2 = answers.get("column2", [])
            if any(_has_media(a.get("content", "")) for a in col2 if isinstance(a, dict)):
                requires_media = True
            # correct_answer: show which col1 terms were wrongly matched (or full pairs if text)
            correct_pairs = []
            for i, a in enumerate(col1):
                if not isinstance(a, dict):
                    continue
                c1_text = _strip_html(a.get("content", "")) or f"item_{i+1}"
                correct_idx = int(a.get("is_true", 0))
                c2_item = col2[correct_idx - 1] if 0 < correct_idx <= len(col2) else {}
                c2_text = _strip_html(c2_item.get("content", "")) if isinstance(c2_item, dict) else ""
                correct_pairs.append(f"{c1_text}→{c2_text}" if c2_text else c1_text)
            correct_answer = "; ".join(correct_pairs) or None
            # student_ans: list the col1 terms the student matched incorrectly
            wrong_terms = []
            for i, item in enumerate(student_items):
                if item.get("is_correct") == 0 and i < len(col1):
                    c1 = col1[i]
                    c1_text = _strip_html(c1.get("content", "")) if isinstance(c1, dict) else ""
                    wrong_terms.append(c1_text or f"item_{i+1}")
            student_ans = f"wrong: {', '.join(wrong_terms)}" if wrong_terms else None

    elif qt == "Kéo thả vào chỗ trống trong đoạn văn":
        # bai_lam: [{u: col2_index (1-based), is_correct:...}, ...] per slot
        # answers.column2 holds the pieces; answers.correctAnswer is the target word/phrase
        if isinstance(answers, dict):
            correct_answer = _strip_html(answers.get("correctAnswer", "")) or None
            col2 = answers.get("column2", [])
            pieces = [
                a.get("content_text") or a.get("content") or _strip_html(a.get("raw_content", ""))
                for a in col2 if isinstance(a, dict)
            ]
            if not question_text or "[{}]" in question_text:
                question_text = "Reorder: " + " | ".join(p for p in pieces if p)
            # Reconstruct student's assembled sequence from slot indices
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

    # Skill breakdown by question_folder
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
        f for f, s in skill_breakdown.items()
        if s["accuracy"] is not None and s["accuracy"] < 0.70
    ]

    # Failed questions with full content extraction
    failed_questions = []
    for lms_entry in [bai_tap_meta, luyen_tap_meta]:
        pid = lms_entry.get("lms_id")
        if not pid:
            continue
        failed = [r for r in detail_by_pid.get(pid, []) if r.get("is_correct") == 0]
        for row in failed[:WORST_LMS_Q_LIMIT]:
            content = extract_question_content(row)
            failed_questions.append({
                "practice_id": pid,
                "question_id": row.get("question_id"),
                "question_folder": row.get("question_folder"),
                "question_type": row.get("question_type"),
                **content,
            })
        if len(failed_questions) >= WORST_LMS_Q_LIMIT:
            break

    attempted = bai_tap is not None or luyen_tap is not None

    # When no attempt exists, pull a question preview from the bank so the
    # agent knows what content is in the lesson without detail records.
    not_attempted_preview = {}
    if not attempted and question_bank_by_pid:
        for section_name, lms_entry in [("bai_tap", bai_tap_meta), ("luyen_tap", luyen_tap_meta)]:
            pid = lms_entry.get("lms_id")
            if not pid:
                continue
            bank_qs = (question_bank_by_pid.get(pid) or [])[:QUESTION_BANK_PREVIEW_LIMIT]
            if bank_qs:
                not_attempted_preview[section_name] = []
                for q in bank_qs:
                    content = extract_question_content(q)
                    not_attempted_preview[section_name].append({
                        "practice_id": pid,
                        "question_id": q.get("question_id"),
                        "question_folder": q.get("question_folder"),
                        "question_type": q.get("question_type"),
                        "status": "not_attempted",
                        **content,
                    })

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


def compute_session_metrics(sessions, results):
    """
    Session-level aggregates (Digital Teacher) — keep in sync with export_questions.compute_session_metrics.
    Used in student_context.in_class for history UI and parity with questions_export.
    """
    if not sessions:
        return None

    def _ts(s):
        for key in ("lastActiveAt", "updatedAt", "startedAt"):
            v = s.get(key)
            if isinstance(v, dict):
                d = v.get("$date") or ""
                if d:
                    return d
        return ""

    latest = max(sessions, key=_ts)
    ck = latest.get("checkpoint") or {}
    audio = [r for r in results if r.get("interactionType") == "AUDIO"]
    rts = [r["reactionTimeMs"] for r in audio if isinstance(r.get("reactionTimeMs"), (int, float))]
    return {
        "cups": ck.get("currentCups"),
        "audio_turns": len(audio),
        "avg_reaction_ms": int(round(sum(rts) / len(rts))) if rts else None,
        "fastest_reaction_ms": int(min(rts)) if rts else None,
        "total_duration_ms": latest.get("totalDurationMs"),
        "session_status": latest.get("status"),
        "completion_pct": latest.get("completionPercentage"),
    }


def _build_speaking_item(r, lms_type):
    """Build a worst_speaking_items entry with system and student data clearly separated."""
    result_data = r.get("result") or {}
    lms_data = r.get("lmsData") or {}
    ad = result_data.get("additionalData") or {}

    # Brainstorm: extract target vocabulary objects and which ones the student got right
    target_objects = None
    correct_objects = None
    if "brainstorm" in ad:
        bst = ad["brainstorm"]
        objs = bst.get("objects") or []
        target_objects = [
            o["name"] for o in objs if isinstance(o, dict) and o.get("isMain")
        ] or None
        correct_objects = (bst.get("result") or {}).get("correctObjects") or None

    return {
        # System data: what the platform expected
        "lms_type": lms_type,
        "question": lms_data.get("question"),
        "expected_answer": lms_data.get("expectedTranscript"),
        "target_objects": target_objects,
        # Student data: what the student actually produced
        "user_transcript": result_data.get("userTranscript"),
        "score": result_data.get("score"),
        "answer_type": (
            extract_user_answer_type(ad) if lms_type in ("free_speaking", "brainstorm") else None
        ),
        "correct_objects": correct_objects,
        "pronunciation_score": result_data.get("pronunciationScore"),
        "grammar_score": result_data.get("grammarScore"),
        "timestamp": iso_to_date(parse_mongo_date(r.get("timestamp"))),
        # Parity with questions_export speaking rows (homework / history UI)
        "audio_url": result_data.get("audioUrl"),
        "reaction_time_ms": r.get("reactionTimeMs"),
    }


def build_dt_in_class(sessions, results):
    if not sessions:
        return {"participated": False}

    completed_sessions = [s for s in sessions if s.get("status") == "COMPLETED"]
    latest_session = max(sessions, key=lambda s: parse_mongo_date(s.get("startedAt", "")))
    latest_date = iso_to_date(parse_mongo_date(latest_session.get("startedAt")))
    max_completion = max(s.get("completionPercentage", 0) for s in sessions)

    audio_results = [r for r in results if r.get("interactionType") == "AUDIO"]

    # Pronunciation drills
    pron_items = [r for r in audio_results if classify_audio(r) == "pronunciation_drill"]
    pron_scores = [
        r["result"]["pronunciationScore"]
        for r in pron_items
        if (r.get("result") or {}).get("pronunciationScore") is not None
    ]
    pronunciation_score_avg = (
        round(sum(pron_scores) / len(pron_scores), 2) if pron_scores else None
    )

    # Warmup / unscripted free speaking (NOT brainstorm — see brainstorm_* below)
    free_items = [r for r in audio_results if classify_audio(r) == "free_speaking"]
    free_scores = [
        r["result"]["score"]
        for r in free_items
        if (r.get("result") or {}).get("score") is not None
    ]
    free_speaking_score_avg = (
        round(sum(free_scores) / len(free_scores), 2) if free_scores else None
    )

    answer_type_dist = defaultdict(int)
    for r in free_items:
        uat = extract_user_answer_type((r.get("result") or {}).get("additionalData"))
        if uat:
            answer_type_dist[uat] += 1

    # Brainstorm: look at image / cues and name target vocabulary (objects in additionalData)
    brainstorm_items = [r for r in audio_results if classify_audio(r) == "brainstorm"]
    brainstorm_scores = [
        r["result"]["score"]
        for r in brainstorm_items
        if (r.get("result") or {}).get("score") is not None
    ]
    brainstorm_score_avg = (
        round(sum(brainstorm_scores) / len(brainstorm_scores), 2) if brainstorm_scores else None
    )
    brainstorm_answer_type_dist = defaultdict(int)
    for r in brainstorm_items:
        uat = extract_user_answer_type((r.get("result") or {}).get("additionalData"))
        if uat:
            brainstorm_answer_type_dist[uat] += 1

    # Conversation (structured dialogue with grammar + pronunciation scoring)
    convo_items = [r for r in audio_results if classify_audio(r) == "conversation"]
    convo_scores = [
        r["result"]["score"]
        for r in convo_items
        if (r.get("result") or {}).get("score") is not None
    ]
    conversation_score_avg = (
        round(sum(convo_scores) / len(convo_scores), 2) if convo_scores else None
    )

    # Collect failures: warmup / brainstorm score==0, conversation score<70
    failed_free = [
        r for r in free_items
        if (r.get("result") or {}).get("score", 1) == 0
    ]
    failed_brainstorm = [
        r for r in brainstorm_items
        if (r.get("result") or {}).get("score", 1) == 0
    ]
    failed_convo = [
        r for r in convo_items
        if ((r.get("result") or {}).get("score") or 100) < 70
    ]
    all_failed = (
        [(r, "free_speaking") for r in failed_free]
        + [(r, "brainstorm") for r in failed_brainstorm]
        + [(r, "conversation") for r in failed_convo]
    )
    all_failed_sorted = sorted(
        all_failed,
        key=lambda x: parse_mongo_date(x[0].get("timestamp", "")),
        reverse=True,
    )
    worst_speaking_items = [
        _build_speaking_item(r, lms_type)
        for r, lms_type in all_failed_sorted[:WORST_SPEAKING_LIMIT]
    ]

    return {
        "participated": True,
        "session_count": len(sessions),
        "session_metrics": compute_session_metrics(sessions, results),
        "is_completed": len(completed_sessions) > 0,
        "completion_pct": max_completion,
        "latest_session_date": latest_date,
        "pronunciation_attempts": len(pron_items),
        "pronunciation_score_avg": pronunciation_score_avg,
        "free_speaking_attempts": len(free_items),
        "free_speaking_score_avg": free_speaking_score_avg,
        "free_speaking_answer_type_dist": dict(answer_type_dist),
        "brainstorm_attempts": len(brainstorm_items),
        "brainstorm_score_avg": brainstorm_score_avg,
        "brainstorm_answer_type_dist": dict(brainstorm_answer_type_dist),
        "conversation_attempts": len(convo_items),
        "conversation_score_avg": conversation_score_avg,
        "worst_speaking_items": worst_speaking_items,
    }


def derive_status(in_class, homework):
    has_dt = in_class.get("participated", False)
    has_hw = homework.get("attempted", False)
    if has_dt and has_hw:
        return "completed"
    if has_dt and not has_hw:
        return "in_class_only"
    if not has_dt and has_hw:
        return "homework_only"
    return "not_started"


def compute_weakness_score(homework, in_class) -> float:
    """
    Composite weakness 0.0–1.0 (higher = weaker).
    Weights: bai_tap 35%, luyen_tap 15%, spoken production 50%
    Spoken component uses the weaker of warmup free_speaking vs brainstorm (conservative).
    """
    components = []

    bt = homework.get("bai_tap") or {}
    if bt.get("score") is not None:
        components.append((1.0 - bt["score"], 0.35))

    lt = homework.get("luyen_tap") or {}
    if lt.get("score") is not None:
        components.append((1.0 - lt["score"], 0.15))

    fs = in_class.get("free_speaking_score_avg")
    bs = in_class.get("brainstorm_score_avg")
    spoken = None
    if fs is not None and bs is not None:
        spoken = min(fs, bs)
    elif fs is not None:
        spoken = fs
    elif bs is not None:
        spoken = bs
    if spoken is not None:
        components.append((1.0 - spoken / 100.0, 0.50))
    elif in_class.get("participated"):
        # Participated but no free speaking data: use pronunciation as weak proxy
        pron = in_class.get("pronunciation_score_avg")
        if pron is not None:
            components.append((1.0 - pron / 100.0, 0.25))

    if not components:
        return 0.0

    total_weight = sum(w for _, w in components)
    weighted_sum = sum(score * w for score, w in components)
    return round(weighted_sum / total_weight, 4)


def latest_activity_date(*dates):
    valid = [d for d in dates if d]
    return max(valid) if valid else None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_student_context():
    print("Loading data files...")
    tutor_by_lesson, _ = load_tutor_lessons()
    pr_by_pid = load_lms_practice_results()
    detail_by_pid = load_lms_detail()
    dt_sessions = load_dt_sessions()
    dt_results = load_dt_results()
    question_bank_by_pid = load_question_bank()

    # tutor_lessons = lessons the student is enrolled in (has lms_id for homework)
    # dt_sessions   = lessons the student entered a Digital Teacher session for
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

        # Scoring for forgetting curve + weakness
        days_since = None
        f_score = None
        w_score = None
        composite = None
        if last_date_str:
            days_since = (TODAY - date.fromisoformat(last_date_str)).days
            f_score = forgetting_score(days_since)
            w_score = compute_weakness_score(homework, in_class)
            composite = round(0.5 * f_score + 0.5 * w_score, 4)

        records.append({
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
        })

    # Drop future-scheduled lessons (enrolled but no activity yet)
    records = [r for r in records if r["status"] != "not_started"]

    # Sort by composite DESC (most urgent review first), then by recency
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
            # Separate text-renderable vs media-dependent failed questions
            all_failed = hw.get("worst_questions", [])
            text_questions = [q for q in all_failed if not q.get("requires_media")]
            media_questions = [q for q in all_failed if q.get("requires_media")]
            question_bank_preview = []
        else:
            # No homework attempt: surface question bank preview so the agent
            # knows what the lesson covers and can assign it as new homework
            all_failed = []
            text_questions = []
            media_questions = []
            preview = hw.get("not_attempted_preview", {})
            question_bank_preview = []
            for section_qs in preview.values():
                question_bank_preview.extend(section_qs)
            question_bank_preview = question_bank_preview[:WORST_LMS_Q_LIMIT]

            # Skip session-only lessons with no lms mapping — no homework can be assigned
            if not lms_ids.get("bai_tap") and not lms_ids.get("luyen_tap"):
                continue

        candidates.append({
            "lesson_id": r["lesson_id"],
            "title": r["title"],
            "level": r["level"],
            "last_activity_date": r.get("last_activity_date"),
            "days_since_last_practice": r["days_since_last_practice"],
            "forgetting_score": r["forgetting_score"],
            "weakness_score": r["weakness_score"],
            "composite_priority_score": r["composite_priority_score"],
            # "not_attempted" means student attended class but has not done homework
            "homework_status": homework_status,
            "weak_skills": hw.get("weak_skills", []),
            # Text-based failed questions (agent can present directly); empty when not attempted
            "failed_text_questions": text_questions,
            # Question bank preview for not-attempted lessons (status="not_attempted" per item)
            "question_bank_preview": question_bank_preview,
            # Media-dependent questions (agent notes topic but can't show inline)
            "failed_media_questions_count": len(media_questions),
            # Worst speaking items (already text — transcript + question)
            "worst_speaking_items": r["in_class"].get("worst_speaking_items", []),
            # Practice IDs for reference (falls back to lms_ids when no attempt exists)
            "practice_ids": {
                "bai_tap": bt.get("practice_id") or lms_ids.get("bai_tap"),
                "luyen_tap": lt.get("practice_id") or lms_ids.get("luyen_tap"),
            },
        })

    # Smart filtering: content gate + score threshold + hard ceiling
    # Content gate: must have at least one actionable item
    candidates = [
        c for c in candidates
        if (
            c.get("failed_text_questions")
            or c.get("question_bank_preview")
            or c.get("worst_speaking_items")
            or c.get("failed_media_questions_count", 0) > 0
        )
    ]
    # Score threshold: only meaningful candidates; fall back to floor if too few
    above = [c for c in candidates if (c["composite_priority_score"] or 0) >= MIN_CANDIDATE_SCORE]
    below = [c for c in candidates if (c["composite_priority_score"] or 0) < MIN_CANDIDATE_SCORE]
    pool = above if len(above) >= MIN_CANDIDATE_POOL_FALLBACK else above + below[:MIN_CANDIDATE_POOL_FALLBACK - len(above)]
    return pool[:MAX_CANDIDATE_POOL_SIZE]


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
        f for f, s in overall_skill.items()
        if s["accuracy"] is not None and s["accuracy"] < 0.70
    ]

    all_pron_scores, all_free_scores, all_brain_scores, all_convo_scores = [], [], [], []
    all_answer_types = defaultdict(int)
    all_brain_answer_types = defaultdict(int)
    for r in records:
        ic = r.get("in_class", {})
        pron_avg = ic.get("pronunciation_score_avg")
        pron_n = ic.get("pronunciation_attempts", 0)
        if pron_avg is not None and pron_n > 0:
            all_pron_scores.extend([pron_avg] * pron_n)
        free_avg = ic.get("free_speaking_score_avg")
        free_n = ic.get("free_speaking_attempts", 0)
        if free_avg is not None and free_n > 0:
            all_free_scores.extend([free_avg] * free_n)
        br_avg = ic.get("brainstorm_score_avg")
        br_n = ic.get("brainstorm_attempts", 0)
        if br_avg is not None and br_n > 0:
            all_brain_scores.extend([br_avg] * br_n)
        convo_avg = ic.get("conversation_score_avg")
        convo_n = ic.get("conversation_attempts", 0)
        if convo_avg is not None and convo_n > 0:
            all_convo_scores.extend([convo_avg] * convo_n)
        for at, cnt in ic.get("free_speaking_answer_type_dist", {}).items():
            all_answer_types[at] += cnt
        for at, cnt in ic.get("brainstorm_answer_type_dist", {}).items():
            all_brain_answer_types[at] += cnt

    return {
        "student_id": STUDENT_ID,
        "reference_date": str(TODAY),
        "total_lessons": total,
        "lessons_by_status": dict(by_status),
        "overall_homework_skill_breakdown": overall_skill,
        "weak_skills_global": weak_skills_global,
        "overall_pronunciation_score_avg": (
            round(sum(all_pron_scores) / len(all_pron_scores), 2) if all_pron_scores else None
        ),
        "overall_free_speaking_score_avg": (
            round(sum(all_free_scores) / len(all_free_scores), 2) if all_free_scores else None
        ),
        "overall_brainstorm_score_avg": (
            round(sum(all_brain_scores) / len(all_brain_scores), 2) if all_brain_scores else None
        ),
        "overall_conversation_score_avg": (
            round(sum(all_convo_scores) / len(all_convo_scores), 2) if all_convo_scores else None
        ),
        "overall_free_speaking_answer_type_dist": dict(all_answer_types),
        "overall_brainstorm_answer_type_dist": dict(all_brain_answer_types),
        "forgetting_curve_note": (
            "All lessons have 1 prior attempt. Stability set to default 1 day. "
            "Lessons older than 7 days score >0.999 (fully forgotten). "
            "Agent should prioritise by composite_priority_score."
        ),
    }


def main():
    global DATA_DIR, STUDENT_ID, OUTPUT_FILE

    import argparse
    import os

    parser = argparse.ArgumentParser(description="Preprocess student learning data.")
    parser.add_argument(
        "student_id", nargs="?", type=str, default="2102555",
        help="Student data folder under data/ (e.g. 2102555 or 2111414_newstudent). Default: 2102555",
    )
    args = parser.parse_args()

    STUDENT_ID = str(args.student_id).strip()
    DATA_DIR = f"data/{STUDENT_ID}"
    OUTPUT_FILE = f"output/{STUDENT_ID}/student_context.json"

    os.makedirs(f"output/{STUDENT_ID}", exist_ok=True)

    records = build_student_context()
    summary = build_summary(records)
    scored_candidates = build_scored_candidates(records)

    output = {
        "summary": summary,
        "scored_candidates": scored_candidates,
        "lessons": records,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(records)} lessons → {OUTPUT_FILE}")
    print(f"Status: {summary['lessons_by_status']}")
    print(f"Scored candidates (Agent 2 pool): {len(scored_candidates)}")
    print(f"Pronunciation avg: {summary['overall_pronunciation_score_avg']}")
    print(f"Free speaking (warmup) avg: {summary['overall_free_speaking_score_avg']}")
    print(f"Brainstorm (ảnh→từ) avg:     {summary['overall_brainstorm_score_avg']}")
    print(f"Conversation avg:  {summary['overall_conversation_score_avg']}")
    print(f"Global weak skills: {summary['weak_skills_global']}")
    print(f"\nTop 5 priority lessons for re-practice:")
    for r in [c for c in scored_candidates if c["composite_priority_score"]][:5]:
        print(
            f"  [{r['composite_priority_score']:.3f}] lesson {r['lesson_id']} "
            f"'{(r['title'] or '')[:45]}' "
            f"| forget={r['forgetting_score']:.3f} weak={r['weakness_score']:.3f} "
            f"| {r['days_since_last_practice']}d ago"
        )


if __name__ == "__main__":
    main()
