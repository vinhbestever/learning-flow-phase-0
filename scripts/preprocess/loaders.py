import glob
import json
from collections import defaultdict

from . import config


def _normalize_tutor_section_type(raw: str) -> str:
    """Map export-specific labels onto Bài tập / Luyện tập for downstream logic."""
    s = (raw or "").strip()
    if not s:
        return s
    mapped = config.SECTION_TYPE_MAP.get(s, s)
    if mapped in ("Bài tập", "Luyện tập"):
        return mapped
    low = s.lower()
    if low.endswith("homework") or " - homework" in low:
        return "Bài tập"
    if "luyện tập" in low or low.endswith("practice"):
        return "Luyện tập"
    return mapped


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
    paths = sorted(glob.glob(f"{config.DATA_DIR}/tutor_lesson*.json"))
    if not paths:
        return {}, {}

    all_items = []
    for path in paths:
        all_items.extend(load_json(path))

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
            lesson_title = ""
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
    for path in sorted(glob.glob(f"{config.DATA_DIR}/lms_practice_result*.json")):
        if "detail" in path:
            continue
        for r in load_json(path):
            results[r["practice_id"]] = r
    return results


def load_lms_detail():
    """Returns dict: practice_id -> [detail_row, ...]."""
    detail = defaultdict(list)
    for path in sorted(glob.glob(f"{config.DATA_DIR}/lms_practice_result_detail*.json")):
        for row in load_json(path):
            detail[row["practice_id"]].append(row)
    return detail


def load_dt_sessions():
    """Returns dict: lesson_id (int) -> [session, ...]."""
    by_lesson = defaultdict(list)
    for path in sorted(glob.glob(f"{config.DATA_DIR}/vh_digital_teacher.learning_sessions*.json")):
        for s in load_json(path):
            eid = s.get("erpLessonId", "")
            if str(eid).isdigit():
                by_lesson[int(eid)].append(s)
    return by_lesson


def load_dt_results():
    """Returns dict: lesson_id (int) -> [result, ...]."""
    by_lesson = defaultdict(list)
    for path in sorted(glob.glob(f"{config.DATA_DIR}/vh_digital_teacher.learning_results*.json")):
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
        items = load_json(config.QUESTION_BANK_PATH)
    except (FileNotFoundError, OSError):
        return {}
    bank = defaultdict(list)
    for q in items:
        pid = q.get("practice_id")
        if pid is not None:
            bank[pid].append(q)
    return dict(bank)
