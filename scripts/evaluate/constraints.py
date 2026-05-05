from __future__ import annotations

import re
from collections import Counter, defaultdict

_VN_RE = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ"
    r"ÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]"
)


def evaluate_constraints(homework_list: list[dict], cand_map: dict) -> dict:
    checks: dict[str, bool] = {}

    checks["count_15"] = len(homework_list) == 15

    skill_counts = Counter(q["skill_category"] for q in homework_list)
    checks["speaking_ge3"] = skill_counts.get("speaking", 0) >= 3
    checks["grammar_ge4"] = skill_counts.get("grammar", 0) >= 4
    checks["vocab_ge3"] = skill_counts.get("vocabulary", 0) >= 3

    lesson_qs: dict[int, list[dict]] = defaultdict(list)
    for q in homework_list:
        lesson_qs[q["lesson_id"]].append(q)

    per_lesson_max = max((len(v) for v in lesson_qs.values()), default=0)
    checks["per_lesson_le2"] = per_lesson_max <= 2

    paired_violations: list[int] = []
    for lid, qs in lesson_qs.items():
        if len(qs) >= 2:
            skills = [q["skill_category"] for q in qs]
            if len(set(skills)) < len(skills):
                paired_violations.append(lid)
    checks["different_skills_when_paired"] = len(paired_violations) == 0

    media_count = sum(1 for q in homework_list if q.get("requires_media"))
    checks["media_count_le4"] = media_count <= 4

    n_vn = sum(1 for q in homework_list if _VN_RE.search(q.get("reason", "")))
    checks["all_reasons_vietnamese"] = n_vn == len(homework_list)

    invalid_lesson_ids = [q["lesson_id"] for q in homework_list if q["lesson_id"] not in cand_map]
    checks["valid_lesson_ids"] = len(invalid_lesson_ids) == 0

    score = sum(1 for v in checks.values() if v) / max(len(checks), 1)

    return {
        "score": round(score, 4),
        "passed": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "checks": checks,
        "skill_distribution": dict(skill_counts),
        "per_lesson_max": per_lesson_max,
        "media_count": media_count,
        "reasons_vn_count": n_vn,
        "paired_skill_violations": paired_violations,
        "invalid_lesson_ids": invalid_lesson_ids,
    }
