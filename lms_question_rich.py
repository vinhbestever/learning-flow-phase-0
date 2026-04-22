"""
Structured media / choice previews from LMS HTML question rows.

Used by preprocess.extract_question_content and export_questions.extract_lms_question.
"""

from __future__ import annotations

import json
import re
from typing import Any

_IMG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
_AUDIO_SRC = re.compile(
    r"<(?:audio|source)[^>]+src=[\"']([^\"']+)[\"']",
    re.I,
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    for entity, char in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&#160;", " "),
    ):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def extract_media_urls(html: str) -> list[str]:
    """Collect image + embedded audio source URLs from HTML (order preserved, unique)."""
    if not html:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for rx in (_IMG_SRC, _AUDIO_SRC):
        for m in rx.finditer(html):
            u = (m.group(1) or "").strip()
            if u and u not in seen:
                seen.add(u)
                out.append(u)
    return out


def _append_choice(
    out: list[dict],
    letter: str,
    content_html: str,
    answer_audio_url: str | None,
) -> None:
    imgs = extract_media_urls(content_html)
    auds: list[str] = []
    if answer_audio_url and str(answer_audio_url).strip():
        u = str(answer_audio_url).strip()
        auds.append(u)
    out.append(
        {
            "letter": letter,
            "text": _strip_html(content_html) or None,
            "image_urls": imgs[:6],
            "audio_urls": auds[:3],
        }
    )


def build_choice_previews(question_type: str, raw_answers: Any) -> list[dict]:
    """
    Flatten LMS `answers` JSON into display rows (text + image/audio URLs per option).

    Supports list-based (single/multi choice, voice) and dict-based (matching / drag).
    """
    try:
        answers = json.loads(raw_answers) if isinstance(raw_answers, str) else raw_answers
    except Exception:
        answers = []

    out: list[dict] = []

    if isinstance(answers, list):
        for i, a in enumerate(answers):
            if isinstance(a, str):
                _append_choice(out, chr(65 + i) if i < 26 else str(i + 1), a, None)
            elif isinstance(a, dict):
                letter = chr(65 + i) if i < 26 else str(i + 1)
                html = a.get("content") or a.get("raw_content") or ""
                _append_choice(out, letter, html, a.get("answer_audio_url"))
        return out[:14]

    if not isinstance(answers, dict):
        return []

    if question_type == "Xứng-Hợp":
        col_labels = ("column1", "column2")
        prefixes = ("A", "B")
        for prefix, col_key in zip(prefixes, col_labels):
            col = answers.get(col_key) or []
            if not isinstance(col, list):
                continue
            for i, a in enumerate(col):
                if not isinstance(a, dict):
                    continue
                html = a.get("raw_content") or a.get("content") or ""
                _append_choice(out, f"{prefix}{i + 1}", html, a.get("answer_audio_url"))
        return out[:20]

    if question_type == "Kéo thả vào chỗ trống trong đoạn văn":
        for i, a in enumerate(answers.get("column2") or []):
            if isinstance(a, dict):
                html = a.get("raw_content") or a.get("content") or ""
                _append_choice(out, str(i + 1), html, None)
        return out[:14]

    return out


def rich_question_fields(
    row: dict,
    *,
    stem_html: str,
    question_type: str,
    raw_answers: Any,
    cap_stem: int = 10,
    cap_comment: int = 6,
    cap_choices: int = 14,
) -> dict:
    """Return extra JSON fields for API / export (plain URLs only, no raw HTML)."""
    comment = row.get("comment") or ""
    stem_urls = extract_media_urls(stem_html)[:cap_stem]
    comment_urls = extract_media_urls(comment)[:cap_comment]
    choices = build_choice_previews(question_type, raw_answers)[:cap_choices]
    return {
        "stem_media_urls": stem_urls,
        "comment_media_urls": comment_urls,
        "choice_previews": choices,
    }
