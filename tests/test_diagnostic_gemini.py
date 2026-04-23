import asyncio
import types

import pytest

import agents.diagnostic_gemini as mod


class _Chunk:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


class _Stream:
    def __init__(self, parts: list[str]) -> None:
        self._parts = parts
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> _Chunk:
        if self._i >= len(self._parts):
            raise StopAsyncIteration
        t = self._parts[self._i]
        self._i += 1
        return _Chunk(t)


class _Models:
    def __init__(self, parts: list[str]) -> None:
        self._parts = parts

    async def generate_content_stream(self, **kwargs) -> _Stream:
        return _Stream(self._parts)


class _Aio:
    def __init__(self, parts: list[str]) -> None:
        self.models = _Models(parts)


class _Client:
    def __init__(self, parts: list[str]) -> None:
        self.aio = _Aio(parts)


def test_stream_diagnostic_gemini_streams_tokens(monkeypatch) -> None:
    sent: list[str] = []

    async def send(t: str) -> None:
        sent.append(t)

    def fake_client(**_kw) -> _Client:
        return _Client(["Hel", "lo"])

    monkeypatch.setattr(mod, "genai", types.SimpleNamespace(Client=fake_client))

    async def _go() -> str:
        return await mod.stream_diagnostic_gemini(
            model="gemini-2.5-flash",
            system_instruction="sys",
            user_content="user",
            send_token=send,
            api_key="test-key",
        )

    out = asyncio.run(_go())
    assert out == "Hello"
    assert sent == ["Hel", "lo"]


def test_stream_diagnostic_gemini_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    async def send(_t: str) -> None:
        return None

    async def go() -> None:
        await mod.stream_diagnostic_gemini(
            model="gemini-2.5-flash",
            system_instruction="a",
            user_content="b",
            send_token=send,
            api_key=None,
        )

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        asyncio.run(go())
