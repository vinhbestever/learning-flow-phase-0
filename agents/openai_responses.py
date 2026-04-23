"""
OpenAI /v1/responses — bắt buộc với một số model không hỗ trợ /v1/chat/completions
(ví dụ biến thể *-pro / reasoning).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI, OpenAI

from agents.model_config import openai_responses_include_temperature


async def stream_diagnostic_text(
    client: "AsyncOpenAI",
    model: str,
    *,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.4,
    send_token: Callable[[str], Awaitable[None]],
) -> str:
    """Stream chẩn đoán; gửi từng delta qua send_token; trả về full text."""
    out: list[str] = []
    req: dict = {
        "model": model,
        "instructions": system_prompt,
        "input": user_content,
        "stream": True,
    }
    if openai_responses_include_temperature(model):
        req["temperature"] = temperature
    stream = await client.responses.create(**req)
    async for event in stream:
        et = getattr(event, "type", None)
        if et == "response.output_text.delta":
            d = event.delta
            if d:
                out.append(d)
                await send_token(d)
        elif et == "error":
            msg = getattr(event, "message", "OpenAI Responses stream error")
            raise RuntimeError(msg)
    text = "".join(out)
    if not text.strip():
        raise ValueError("Empty response from OpenAI Responses diagnostic stream")
    return text


def complete_diagnostic_text(
    client: "OpenAI",
    model: str,
    *,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.4,
) -> str:
    """Một lần gọi, không stream (agent_pipeline CLI)."""
    req: dict = {
        "model": model,
        "instructions": system_prompt,
        "input": user_content,
    }
    if openai_responses_include_temperature(model):
        req["temperature"] = temperature
    response = client.responses.create(**req)
    text = (response.output_text or "").strip()
    if not text:
        raise ValueError("Empty response from OpenAI Responses diagnostic")
    return text
