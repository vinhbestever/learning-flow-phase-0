"""
Export all questions (in-class + homework) for each lesson the student has studied.

Usage:
    python -m scripts.export_questions [student_id] [--question-bank PATH]
    python export_questions.py ...   (shim at repo root; same behavior)

Output: output/{student_id}/questions_export.json
"""

from . import config
from .bank import load_practice_question_bank
from .homework import build_homework_practice, extract_lms_question
from .in_class import (
    compute_session_metrics,
    extract_brainstorm,
    extract_conversation,
    extract_free_speaking,
    extract_interactive,
    extract_pronunciation_drill,
)
from .pipeline import main
from .text import has_media, strip_html

__all__ = [
    "build_homework_practice",
    "compute_session_metrics",
    "config",
    "extract_brainstorm",
    "extract_conversation",
    "extract_free_speaking",
    "extract_interactive",
    "extract_lms_question",
    "extract_pronunciation_drill",
    "has_media",
    "load_practice_question_bank",
    "main",
    "strip_html",
]
