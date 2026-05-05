"""Backward-compatible re-export. Implementation lives in ``scripts.lms_question_rich``."""

from scripts.lms_question_rich import (  # noqa: F401
    build_choice_previews,
    extract_media_urls,
    rich_question_fields,
)

__all__ = ["build_choice_previews", "extract_media_urls", "rich_question_fields"]
