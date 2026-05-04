"""
Selector using Gemini structured JSON (same schema + prompts as OpenAI path).
"""

from __future__ import annotations

import json
import os

from google import genai
from google.genai import types

from agents.selector_agent import (
    HOMEWORK_SCHEMA,
    MAX_SELECTOR_RETRIES,
    SYSTEM_PROMPT,
    _build_retry_prompt,
    _repair_homework,
    _validate_constraints,
    build_prompt,
    enrich_homework_from_pool,
    parse_response,
)


async def run_selector_gemini(
    diagnostic_text: str,
    question_pool: list,
    model: str,
    save_path: str | None = None,
    api_key: str | None = None,
    min_speaking: int = 3,
) -> list:
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not set")

    prompt = build_prompt(diagnostic_text, question_pool, min_speaking=min_speaking)
    client = genai.Client(api_key=key)
    best_homework = None
    best_violation_count = 999

    for attempt in range(MAX_SELECTOR_RETRIES):
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=HOMEWORK_SCHEMA["schema"],
            ),
        )
        raw = response.text
        homework = parse_response(raw)
        enrich_homework_from_pool(homework, question_pool)

        violations = _validate_constraints(homework, min_speaking)
        if len(violations) < best_violation_count:
            best_homework = homework
            best_violation_count = len(violations)

        if not violations:
            break
        print(f"      [selector retry {attempt + 1}/{MAX_SELECTOR_RETRIES}] violations: {violations}")
        prompt = _build_retry_prompt(diagnostic_text, question_pool, violations, min_speaking)

    homework = best_homework
    remaining = _validate_constraints(homework, min_speaking)
    if remaining:
        print(f"      [selector repair] fixing {len(remaining)} remaining violations: {remaining}")
        homework = _repair_homework(homework, question_pool, min_speaking)
        enrich_homework_from_pool(homework, question_pool)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework


def run_selector_gemini_sync(
    diagnostic_text: str,
    question_pool: list,
    model: str,
    save_path: str | None = None,
    api_key: str | None = None,
    min_speaking: int = 3,
) -> list:
    """Synchronous selector for CLI (uses sync ``generate_content``)."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not set")

    prompt = build_prompt(diagnostic_text, question_pool, min_speaking=min_speaking)
    client = genai.Client(api_key=key)
    best_homework = None
    best_violation_count = 999

    for attempt in range(MAX_SELECTOR_RETRIES):
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=HOMEWORK_SCHEMA["schema"],
            ),
        )
        raw = response.text
        homework = parse_response(raw)
        enrich_homework_from_pool(homework, question_pool)

        violations = _validate_constraints(homework, min_speaking)
        if len(violations) < best_violation_count:
            best_homework = homework
            best_violation_count = len(violations)

        if not violations:
            break
        print(f"      [selector retry {attempt + 1}/{MAX_SELECTOR_RETRIES}] violations: {violations}")
        prompt = _build_retry_prompt(diagnostic_text, question_pool, violations, min_speaking)

    homework = best_homework
    remaining = _validate_constraints(homework, min_speaking)
    if remaining:
        print(f"      [selector repair] fixing {len(remaining)} remaining violations: {remaining}")
        homework = _repair_homework(homework, question_pool, min_speaking)
        enrich_homework_from_pool(homework, question_pool)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"homework": homework}, f, ensure_ascii=False, indent=2)

    return homework
