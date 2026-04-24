"""
Allowlisted LLM ids for the homework pipeline and provider resolution.

Only current-generation models (no legacy 4o / 1.5 / 2.0 lanes). Update when
providers add successors — see https://platform.openai.com/docs/models and
https://ai.google.dev/gemini-api/docs/models
"""

from __future__ import annotations

# OpenAI: frontier + GPT-4.1 family (best general + efficient variants; no 4o/o3)
OPENAI_MODELS: frozenset[str] = frozenset(
    {
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
    }
)

# Google: Gemini 2.5+ (2.0 / 1.5 removed from selection)
GOOGLE_MODELS: frozenset[str] = frozenset(
    {
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.1-pro-preview",
    }
)

ALL_ALLOWED: frozenset[str] = OPENAI_MODELS | GOOGLE_MODELS

# Default for new pipeline runs (must be in OPENAI_MODELS)
DEFAULT_HOMEWORK_MODEL = "gpt-5.4"

# Chỉ hỗ trợ /v1/responses, không dùng /v1/chat/completions (lỗi 404 "not a chat model")
OPENAI_RESPONSES_ONLY: frozenset[str] = frozenset(
    {
        "gpt-5.4-pro",
    }
)

# Một số model Responses từ chối tham số `temperature` (400 unsupported parameter)
OPENAI_RESPONSES_OMIT_TEMPERATURE: frozenset[str] = frozenset(
    {
        "gpt-5.4-pro",
    }
)


def is_allowed(model_id: str) -> bool:
    return model_id in ALL_ALLOWED


def openai_uses_responses_api(model_id: str) -> bool:
    return model_id in OPENAI_RESPONSES_ONLY


def openai_responses_include_temperature(model_id: str) -> bool:
    """False → không gửi `temperature` trong /v1/responses."""
    return model_id not in OPENAI_RESPONSES_OMIT_TEMPERATURE


def get_provider(model_id: str) -> str:
    if model_id in OPENAI_MODELS:
        return "openai"
    if model_id in GOOGLE_MODELS:
        return "google"
    raise ValueError(f"Unknown or disallowed model: {model_id!r}")
