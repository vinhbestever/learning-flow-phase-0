"""
Streaming diagnostic using Google GenAI (Gemini) — same prompts as OpenAI path.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from google import genai
from google.genai import types

async def stream_diagnostic_gemini(
    *,
    model: str,
    system_instruction: str,
    user_content: str,
    send_token: Callable[[str], Awaitable[None]],
    temperature: float = 0.4,
    api_key: str | None = None,
) -> str:
    """
    Stream text chunks to ``send_token``; return full diagnostic string.

    Uses cumulative text from each chunk and emits only the delta (Gemini
    stream typically extends ``chunk.text`` monotonically).
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not set")

    client = genai.Client(api_key=key)
    acc = ""
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )
    stream = await client.aio.models.generate_content_stream(
        model=model,
        contents=user_content,
        config=config,
    )
    async for chunk in stream:
        piece = chunk.text or ""
        if piece:
            acc += piece
            await send_token(piece)
    if not acc.strip():
        raise ValueError("Empty response from Gemini diagnostic")
    return acc


def run_diagnostic_gemini_sync(
    *,
    model: str,
    system_instruction: str,
    user_content: str,
    temperature: float = 0.4,
    api_key: str | None = None,
) -> str:
    """Non-streaming diagnostic (CLI / scripts)."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        ),
    )
    t = response.text or ""
    if not t.strip():
        raise ValueError("Empty response from Gemini diagnostic")
    return t
