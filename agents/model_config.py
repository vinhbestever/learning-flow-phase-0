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
        "gpt-5.4-pro",
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

# Default for new pipeline runs (must be in OPENAI_MODELS; legacy imports still use gpt-4o key in storage)
DEFAULT_HOMEWORK_MODEL = "gpt-5.4"


def is_allowed(model_id: str) -> bool:
    return model_id in ALL_ALLOWED


def get_provider(model_id: str) -> str:
    if model_id in OPENAI_MODELS:
        return "openai"
    if model_id in GOOGLE_MODELS:
        return "google"
    raise ValueError(f"Unknown or disallowed model: {model_id!r}")
