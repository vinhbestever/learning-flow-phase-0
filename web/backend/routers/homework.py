import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from web.backend.config import DIAGNOSTIC_PATH as DIAGNOSTIC_PATH
from web.backend.config import HOMEWORK_PATH as HOMEWORK_PATH
from web.backend.config import STUDENT_CONTEXT_PATH as STUDENT_CONTEXT_PATH
from web.backend.pipeline_ws import run_pipeline_ws

router = APIRouter(prefix="/api")


@router.get("/homework")
def get_homework():
    hw_p = Path(HOMEWORK_PATH)
    diag_p = Path(DIAGNOSTIC_PATH)
    if not hw_p.exists() or not diag_p.exists():
        raise HTTPException(
            status_code=404,
            detail="Homework not generated yet — use /generate to run the pipeline",
        )
    hw = json.loads(hw_p.read_text(encoding="utf-8"))
    diag = diag_p.read_text(encoding="utf-8")

    # Enrich with student context if available
    ctx_by_lesson: dict = {}
    ctx_p = Path(STUDENT_CONTEXT_PATH)
    if ctx_p.exists():
        ctx = json.loads(ctx_p.read_text(encoding="utf-8"))
        for c in ctx.get("scored_candidates", []):
            ctx_by_lesson[c["lesson_id"]] = c

    homework_list = hw.get("homework", [])
    for q in homework_list:
        ctx_data = ctx_by_lesson.get(q.get("lesson_id"))
        if ctx_data:
            q["student_context"] = {
                "days_since_last_practice": ctx_data.get("days_since_last_practice"),
                "forgetting_score": ctx_data.get("forgetting_score"),
                "weakness_score": ctx_data.get("weakness_score"),
                "worst_speaking_items": ctx_data.get("worst_speaking_items", []),
                "failed_text_questions": ctx_data.get("failed_text_questions", []),
            }
        else:
            q["student_context"] = None

    return {"homework": homework_list, "diagnostic": diag}


@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    await websocket.accept()

    async def send(msg: dict):
        await websocket.send_json(msg)

    try:
        await run_pipeline_ws(send)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "text": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
