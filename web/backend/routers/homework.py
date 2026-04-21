import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from web.backend.config import DIAGNOSTIC_PATH as DIAGNOSTIC_PATH
from web.backend.config import HOMEWORK_PATH as HOMEWORK_PATH
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
    return {"homework": hw.get("homework", []), "diagnostic": diag}


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
