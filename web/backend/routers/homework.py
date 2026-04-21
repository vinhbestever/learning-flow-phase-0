import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

HOMEWORK_PATH = "output/homework_assignment.json"
DIAGNOSTIC_PATH = "output/diagnostic_output.txt"

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
