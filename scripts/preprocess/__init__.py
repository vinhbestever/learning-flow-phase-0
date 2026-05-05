"""
Preprocess raw learning data for a given student.

Usage:
    python -m scripts.preprocess [student_folder]   (default: 2102555)
    python preprocess.py ...   (shim at repo root; same behavior)

Output: output/{student_id}/student_context.json
"""

from . import config
from .digital_teacher import (
    build_dt_in_class,
    compute_session_metrics,
    compute_weakness_score,
    derive_status,
    latest_activity_date,
)
from .lms_questions import build_lms_homework, extract_question_content
from .loaders import (
    load_dt_results,
    load_dt_sessions,
    load_json,
    load_lms_detail,
    load_lms_practice_results,
    load_question_bank,
    load_tutor_lessons,
)
from .pipeline import build_scored_candidates, build_student_context, build_summary, main
from .scoring import forgetting_score, retention_score
from .transform import classify_audio, extract_user_answer_type, iso_to_date, parse_mongo_date

__all__ = [
    "build_dt_in_class",
    "build_lms_homework",
    "build_scored_candidates",
    "build_student_context",
    "build_summary",
    "classify_audio",
    "compute_session_metrics",
    "compute_weakness_score",
    "config",
    "derive_status",
    "extract_question_content",
    "extract_user_answer_type",
    "forgetting_score",
    "iso_to_date",
    "latest_activity_date",
    "load_dt_results",
    "load_dt_sessions",
    "load_json",
    "load_lms_detail",
    "load_lms_practice_results",
    "load_question_bank",
    "load_tutor_lessons",
    "main",
    "parse_mongo_date",
    "retention_score",
]
