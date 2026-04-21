"""
Async pipeline wrapper for WebSocket streaming.

Emits JSON messages:
  {"type": "step",  "text": "..."}   — progress log line
  {"type": "token", "text": "..."}   — single GPT token
  {"type": "done",  "homework": [...], "diagnostic": "..."}
  {"type": "error", "text": "..."}
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from openai import AsyncOpenAI

from web.backend.config import DIAGNOSTIC_PATH as DIAGNOSTIC_PATH
from web.backend.config import HOMEWORK_PATH as HOMEWORK_PATH
from web.backend.config import QUESTIONS_EXPORT_PATH as QUESTIONS_EXPORT_PATH
from web.backend.config import STUDENT_CONTEXT_PATH as STUDENT_CONTEXT_PATH

_pipeline_lock = asyncio.Lock()


async def run_pipeline_ws(send) -> None:
    """
    send: async callable that accepts a dict and sends it as JSON over WebSocket.
    """
    if _pipeline_lock.locked():
        await send({"type": "error", "text": "Pipeline đang chạy — vui lòng thử lại sau"})
        return

    if not os.environ.get("OPENAI_API_KEY"):
        await send({"type": "error", "text": "OPENAI_API_KEY chưa được cấu hình"})
        return

    for path in (STUDENT_CONTEXT_PATH, QUESTIONS_EXPORT_PATH):
        if not Path(path).exists():
            await send({"type": "error", "text": f"{path} không tồn tại — chạy preprocess.py trước"})
            return

    async with _pipeline_lock:
        await send({"type": "step", "text": "Đang tải dữ liệu..."})

        loop = asyncio.get_running_loop()

        def _load():
            sc = json.loads(Path(STUDENT_CONTEXT_PATH).read_text(encoding="utf-8"))
            qe = json.loads(Path(QUESTIONS_EXPORT_PATH).read_text(encoding="utf-8"))
            return sc, qe

        student_context, questions_export = await loop.run_in_executor(None, _load)

        # Step 1: build context
        await send({"type": "step", "text": "[1/3] Đang phân tích học sinh..."})

        from agents.context_builder import build_context

        def _build():
            return build_context(student_context, questions_export)

        tiered_candidates, question_pool = await loop.run_in_executor(None, _build)

        # Step 2: diagnostic — stream tokens
        await send({"type": "step", "text": "[2/3] Đang chạy diagnostic agent (GPT-4o)..."})

        from agents.diagnostic_agent import SYSTEM_PROMPT, build_prompt

        prompt = build_prompt(student_context["summary"], tiered_candidates)
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

        diagnostic_text = ""
        stream = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
            if token:
                diagnostic_text += token
                await send({"type": "token", "text": token})

        Path(DIAGNOSTIC_PATH).write_text(diagnostic_text, encoding="utf-8")

        # Step 3: selector
        await send({"type": "step", "text": "[3/3] Đang chọn câu hỏi bài tập..."})

        from agents.selector_agent import run_selector

        def _select():
            return run_selector(
                diagnostic_text=diagnostic_text,
                question_pool=question_pool,
                save_path=HOMEWORK_PATH,
            )

        homework = await loop.run_in_executor(None, _select)

        await send({"type": "done", "homework": homework, "diagnostic": diagnostic_text})
