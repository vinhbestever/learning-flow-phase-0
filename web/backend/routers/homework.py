import copy
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from agents.model_config import ALL_ALLOWED, DEFAULT_HOMEWORK_MODEL, GOOGLE_MODELS, OPENAI_MODELS
from web.backend.config import student_paths
from web.backend.homework_storage import load_homework_state
from web.backend.pipeline_ws import run_pipeline_ws

router = APIRouter(prefix="/api")


def _norm_text(s: object) -> str:
    if s is None:
        return ""
    return " ".join(str(s).lower().split())


def _build_export_question_pools(qe_data: dict) -> dict[int, list[dict]]:
    """Per lesson_id: flat list of homework questions (mutated when matching assignment rows)."""
    pools: dict[int, list[dict]] = {}
    for lesson in qe_data.get("lessons") or []:
        lid = lesson.get("lesson_id")
        if lid is None:
            continue
        acc: list[dict] = []
        hw = lesson.get("homework") or {}
        for sec in ("bai_tap", "luyen_tap"):
            block = hw.get(sec) or {}
            pid = block.get("practice_id")
            src = block.get("questions_source") or ""
            for row in block.get("questions") or []:
                e = dict(row)
                e.setdefault("stem_media_urls", [])
                e.setdefault("comment_media_urls", [])
                e.setdefault("choice_previews", [])
                e["homework_section"] = sec
                e["practice_id"] = pid
                e["questions_source"] = src
                acc.append(e)
        if acc:
            pools[int(lid)] = acc
    return pools


def _pop_export_match(pools: dict[int, list[dict]], item: dict) -> dict | None:
    """Take one export row matching assignment item; removes it from pool."""
    lid = item.get("lesson_id")
    if lid is None:
        return None
    pool = pools.get(int(lid))
    if not pool:
        return None
    aid = item.get("question_id")
    if aid is not None:
        for i, r in enumerate(pool):
            if r.get("question_id") == aid:
                return pool.pop(i)
    qt = item.get("question_type") or ""
    qn = _norm_text(item.get("question_text"))
    ca = _norm_text(item.get("correct_answer"))
    idxs = [
        i
        for i, r in enumerate(pool)
        if (r.get("question_type") or "") == qt and _norm_text(r.get("question_text")) == qn
    ]
    if not idxs and ca and ca != "open":
        idxs = [
            i
            for i, r in enumerate(pool)
            if (r.get("question_type") or "") == qt and _norm_text(r.get("correct_answer")) == ca
        ]
    if len(idxs) > 1 and ca and ca != "open":
        narrowed = [i for i in idxs if _norm_text(pool[i].get("correct_answer")) == ca]
        if narrowed:
            idxs = narrowed
    if not idxs:
        return None
    return pool.pop(idxs[0])


def _attach_lms_question(q: dict, matched: dict, ctx_data: dict | None) -> None:
    """Build `lms_question` for the frontend (aligned with lessons API question rows)."""
    lms = {
        "question_id": matched.get("question_id"),
        "question_folder": matched.get("question_folder"),
        "question_type": matched.get("question_type"),
        "question_text": matched.get("question_text"),
        "comment_plain": matched.get("comment_plain"),
        "requires_media": bool(matched.get("requires_media")),
        "correct_answer": matched.get("correct_answer"),
        "stem_media_urls": matched.get("stem_media_urls") or [],
        "comment_media_urls": matched.get("comment_media_urls") or [],
        "choice_previews": matched.get("choice_previews") or [],
        "is_correct": matched.get("is_correct"),
        "detail_result_id": matched.get("detail_result_id"),
        "practice_id": matched.get("practice_id"),
        "questions_source": matched.get("questions_source"),
        "homework_section": matched.get("homework_section"),
    }
    if not (lms.get("correct_answer") or "").strip():
        lms["correct_answer"] = q.get("correct_answer")
    if not (lms.get("question_text") or "").strip():
        lms["question_text"] = q.get("question_text")

    qid = lms.get("question_id")
    if ctx_data and qid is not None:
        for fq in ctx_data.get("failed_text_questions") or []:
            if fq.get("question_id") == qid:
                lms["student_answer"] = fq.get("student_answer")
                lms["is_failed"] = True
                break
    if "is_failed" not in lms:
        lms["is_failed"] = lms.get("is_correct") == 0
    q["lms_question"] = lms


def _enrich_homework_list(homework_list: list, paths: dict) -> list:
    """Return a deep-copied list with ``student_context`` and ``lms_question`` fields."""
    rows = copy.deepcopy(homework_list)
    ctx_by_lesson: dict = {}
    lesson_by_id: dict = {}
    ctx_p = paths["context"]
    if ctx_p.exists():
        ctx = json.loads(ctx_p.read_text(encoding="utf-8"))
        for c in ctx.get("scored_candidates", []):
            ctx_by_lesson[c["lesson_id"]] = c
        for row in ctx.get("lessons", []):
            lid = row.get("lesson_id")
            if lid is not None:
                lesson_by_id[lid] = row

    qe_p = paths["questions"]
    qe_data = json.loads(qe_p.read_text(encoding="utf-8")) if qe_p.exists() else {}
    pools = _build_export_question_pools(qe_data)

    for q in rows:
        lid = q.get("lesson_id")
        ctx_data = ctx_by_lesson.get(lid)
        lesson_row = lesson_by_id.get(lid) if lid is not None else None
        if ctx_data:
            last_dt = ctx_data.get("last_activity_date") or (lesson_row or {}).get(
                "last_activity_date"
            )
            q["student_context"] = {
                "last_activity_date": last_dt,
                "days_since_last_practice": ctx_data.get("days_since_last_practice"),
                "forgetting_score": ctx_data.get("forgetting_score"),
                "weakness_score": ctx_data.get("weakness_score"),
                "worst_speaking_items": ctx_data.get("worst_speaking_items", []),
                "failed_text_questions": ctx_data.get("failed_text_questions", []),
            }
        else:
            q["student_context"] = None

        matched = _pop_export_match(pools, q)
        if matched:
            _attach_lms_question(q, matched, ctx_data)
    return rows


@router.get("/homework-models")
def list_homework_models():
    return {
        "default_model": DEFAULT_HOMEWORK_MODEL,
        "models": [
            {
                "id": mid,
                "provider": "openai" if mid in OPENAI_MODELS else "google",
            }
            for mid in sorted(ALL_ALLOWED)
        ],
    }


@router.get("/students/{student_id}/homework")
def get_homework(student_id: str):
    paths = student_paths(student_id)
    hbm_p = paths["homework_by_model"]
    state = load_homework_state(hbm_p)
    models_raw = state.get("models") or {}
    if not models_raw:
        raise HTTPException(
            status_code=404,
            detail="Bài tập về nhà chưa được tạo — chạy pipeline để tạo bài tập",
        )

    models_out: dict = {}
    for mid, block in models_raw.items():
        hl = _enrich_homework_list(block.get("homework", []), paths)
        models_out[mid] = {
            "diagnostic": block.get("diagnostic", ""),
            "homework": hl,
            "updated_at": block.get("updated_at"),
        }

    last = state.get("last_run_model")
    if last and last in models_out:
        primary = models_out[last]
    else:
        first_key = next(iter(models_out))
        primary = models_out[first_key]
        last = first_key

    return {
        "homework": primary["homework"],
        "diagnostic": primary["diagnostic"],
        "last_run_model": last,
        "models": models_out,
    }


@router.websocket("/ws/students/{student_id}/generate")
async def ws_generate(websocket: WebSocket, student_id: str):
    await websocket.accept()
    q = dict(websocket.query_params)
    model = q.get("model") or DEFAULT_HOMEWORK_MODEL

    async def send(msg: dict):
        await websocket.send_json(msg)

    try:
        await run_pipeline_ws(send, student_id, model)
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
