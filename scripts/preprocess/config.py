"""Mutable run configuration and constants for the preprocess pipeline."""

from datetime import date

# Updated by ``main()``; readers should use ``from . import config`` and ``config.DATA_DIR``.
DATA_DIR = "data"
STUDENT_ID = "2102555"
OUTPUT_FILE = "output/student_context.json"

TODAY = date(2026, 4, 21)
EBBINGHAUS_STABILITY_DAYS = 7.0
WORST_SPEAKING_LIMIT = 5
WORST_LMS_Q_LIMIT = 5
MAX_CANDIDATE_POOL_SIZE = 40
MIN_CANDIDATE_SCORE = 0.50
MIN_CANDIDATE_POOL_FALLBACK = 5
QUESTION_BANK_PATH = "data/practice_question_bank.json"
QUESTION_BANK_PREVIEW_LIMIT = 5

SECTION_TYPE_MAP = {
    "Bài tập": "Bài tập",
    "Luyện tập": "Luyện tập",
    "Bài luyện tập": "Luyện tập",
}
