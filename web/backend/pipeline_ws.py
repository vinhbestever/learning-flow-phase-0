"""
Async pipeline wrapper for WebSocket streaming.

Emits JSON messages:
  {"type": "step",  "text": "..."}   — progress log line
  {"type": "token", "text": "..."}   — single model token
  {"type": "done",  "homework": [...], "diagnostic": "..."}
  {"type": "error", "text": "..."}
"""

from __future__ import annotations

import asyncio
import json
import os

from openai import AsyncOpenAI

from agents.model_config import (
    DEFAULT_HOMEWORK_MODEL,
    get_provider,
    is_allowed,
    openai_uses_responses_api,
)
from web.backend.config import student_paths
from web.backend.homework_storage import save_model_result

_pipeline_lock = asyncio.Lock()


async def run_pipeline_ws(
    send, student_id: int | str, model: str = DEFAULT_HOMEWORK_MODEL
) -> None:
    """
    send: async callable that accepts a dict and sends it as JSON over WebSocket.
    student_id: folder name under output/ (numeric or e.g. 2111414_newstudent).
    """
    paths = student_paths(student_id)

    if not is_allowed(model):
        await send(
            {
                "type": "error",
                "text": f"Model không hợp lệ hoặc chưa được hỗ trợ: {model}",
            }
        )
        return

    try:
        provider = get_provider(model)
    except ValueError as e:
        await send({"type": "error", "text": str(e)})
        return

    if _pipeline_lock.locked():
        await send({"type": "error", "text": "Pipeline đang chạy — vui lòng thử lại sau"})
        return

    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        await send({"type": "error", "text": "OPENAI_API_KEY chưa được cấu hình"})
        return
    if provider == "google" and not os.environ.get("GOOGLE_API_KEY"):
        await send({"type": "error", "text": "GOOGLE_API_KEY chưa được cấu hình"})
        return

    for path in (paths["context"], paths["questions"]):
        if not path.exists():
            await send({"type": "error", "text": f"{path} không tồn tại — chạy preprocess.py trước"})
            return

    async with _pipeline_lock:
        await send({"type": "step", "text": "Đang tải dữ liệu..."})

        loop = asyncio.get_running_loop()

        def _load():
            sc = json.loads(paths["context"].read_text(encoding="utf-8"))
            qe = json.loads(paths["questions"].read_text(encoding="utf-8"))
            return sc, qe

        student_context, questions_export = await loop.run_in_executor(None, _load)

        await send({"type": "step", "text": "[1/3] Đang phân tích học sinh..."})

        from agents.context_builder import build_context

        def _build():
            return build_context(student_context, questions_export)

        tiered_candidates, question_pool = await loop.run_in_executor(None, _build)

        await send({"type": "step", "text": f"[2/3] Đang chạy diagnostic agent ({model})..."})

        from agents.diagnostic_agent import SYSTEM_PROMPT, build_prompt

        prompt = build_prompt(student_context["summary"], tiered_candidates)

        diagnostic_text = ""
        if provider == "openai":
            client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
            if openai_uses_responses_api(model):
                from agents.openai_responses import stream_diagnostic_text

                async def _send_tok(t: str) -> None:
                    await send({"type": "token", "text": t})

                diagnostic_text = await stream_diagnostic_text(
                    client,
                    model,
                    system_prompt=SYSTEM_PROMPT,
                    user_content=prompt,
                    temperature=0.4,
                    send_token=_send_tok,
                )
            else:
                stream = await client.chat.completions.create(
                    model=model,
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
        else:
            from agents.diagnostic_gemini import stream_diagnostic_gemini

            async def _send_tok(t: str) -> None:
                nonlocal diagnostic_text
                diagnostic_text += t
                await send({"type": "token", "text": t})

            diagnostic_text = await stream_diagnostic_gemini(
                model=model,
                system_instruction=SYSTEM_PROMPT,
                user_content=prompt,
                send_token=_send_tok,
            )

        await send({"type": "step", "text": "[3/3] Đang chọn câu hỏi bài tập..."})

        if provider == "openai":
            from agents.selector_agent import run_selector

            def _select():
                return run_selector(
                    diagnostic_text=diagnostic_text,
                    question_pool=question_pool,
                    save_path=str(paths["homework"]),
                    model=model,
                )

            homework = await loop.run_in_executor(None, _select)
        else:
            from agents.selector_gemini import run_selector_gemini

            homework = await run_selector_gemini(
                diagnostic_text=diagnostic_text,
                question_pool=question_pool,
                model=model,
                save_path=str(paths["homework"]),
            )

        save_model_result(
            paths["homework_by_model"],
            model,
            diagnostic_text,
            homework,
        )

        await send({"type": "done", "homework": homework, "diagnostic": diagnostic_text})
