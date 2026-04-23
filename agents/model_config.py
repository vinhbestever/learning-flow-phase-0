"""
Allowlisted LLM ids for the homework pipeline and provider resolution.

Add new model strings here when the product team approves them.
"""

from __future__ import annotations

# OpenAI Chat Completions / Responses-capable models used by diagnostic + selector
OPENAI_MODELS: frozenset[str] = frozenset(
    {
        "gpt-4o",
        "gpt-4.1",
        "gpt-4o-mini",
        "o3-mini",
    }
)

# Google Generative Language API model ids
GOOGLE_MODELS: frozenset[str] = frozenset(
    {
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    }
)

ALL_ALLOWED: frozenset[str] = OPENAI_MODELS | GOOGLE_MODELS


def is_allowed(model_id: str) -> bool:
    return model_id in ALL_ALLOWED


def get_provider(model_id: str) -> str:
    if model_id in OPENAI_MODELS:
        return "openai"
    if model_id in GOOGLE_MODELS:
        return "google"
    raise ValueError(f"Unknown or disallowed model: {model_id!r}")
