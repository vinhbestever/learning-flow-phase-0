import json
import types

import agents.selector_gemini as mod


def _15_q() -> list[dict]:
    out = []
    for i in range(15):
        out.append(
            {
                "question_no": i + 1,
                "lesson_id": 1,
                "lesson_title": "L",
                "skill_category": "grammar",
                "question_type": "fill",
                "question_text": f"Q{i}",
                "correct_answer": "A",
                "difficulty": "easy",
                "reason": "R",
                "question_id": None,
                "requires_media": False,
            }
        )
    return out


def test_run_selector_gemini_parses_json(monkeypatch) -> None:
    pool = _15_q()  # pool content unused when model returns 15; still need non-empty
    text = json.dumps({"homework": _15_q()})

    class _Resp:
        def __init__(self, t: str) -> None:
            self.text = t

    class _Models:
        async def generate_content(self, **kwargs) -> _Resp:
            return _Resp(text)

    class _Aio:
        models = _Models()

    class _Client:
        def __init__(self) -> None:
            self.aio = _Aio()

    monkeypatch.setattr(mod, "genai", types.SimpleNamespace(Client=lambda **kw: _Client()))
    monkeypatch.setenv("GOOGLE_API_KEY", "k")

    async def go() -> list:
        return await mod.run_selector_gemini(
            diagnostic_text="d",
            question_pool=pool,
            model="gemini-2.5-flash",
        )

    import asyncio

    hw = asyncio.run(go())
    assert len(hw) == 15
