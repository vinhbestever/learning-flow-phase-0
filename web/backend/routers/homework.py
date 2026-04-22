import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from web.backend.config import student_paths
from web.backend.pipeline_ws import run_pipeline_ws

router = APIRouter(prefix="/api")


@router.get("/students/{student_id}/homework")
def get_homework(student_id: int):
    paths = student_paths(student_id)
    hw_p = paths["homework"]
    diag_p = paths["diagnostic"]
    if not hw_p.exists() or not diag_p.exists():
        raise HTTPException(
            status_code=404,
            detail="Bài tập về nhà chưa được tạo — chạy pipeline để tạo bài tập",
        )
    hw = json.loads(hw_p.read_text(encoding="utf-8"))
    diag = diag_p.read_text(encoding="utf-8")

    ctx_by_lesson: dict = {}
    ctx_p = paths["context"]
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


@router.websocket("/ws/students/{student_id}/generate")
async def ws_generate(websocket: WebSocket, student_id: int):
    await websocket.accept()

    async def send(msg: dict):
        await websocket.send_json(msg)

    try:
        await run_pipeline_ws(send, student_id)
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
