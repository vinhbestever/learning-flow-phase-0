# Web System Design — Phase 0 Learning Flow

**Date:** 2026-04-21  
**Scope:** Local-only web UI for student learning data and homework generation pipeline

---

## Overview

A single-server web application exposing the existing Python homework agent pipeline through a browser UI. Backend: FastAPI (Python). Frontend: React + Vite. One `uvicorn` process serves both the API and the built frontend static files.

---

## Architecture

```
phase-0-learning-flow/
  web/
    backend/
      main.py              ← FastAPI app entry point; serves static + mounts routers
      routers/
        student.py         ← GET /api/student
        lessons.py         ← GET /api/lessons
        homework.py        ← GET /api/homework, WS /ws/generate
    frontend/
      src/
        pages/
          StudentProfile.tsx     ← Profile + skill breakdown + learning history
          LessonList.tsx          ← Course lesson list
          GenerateHomework.tsx    ← Pipeline trigger + streaming UI
          HomeworkResult.tsx      ← Diagnostic + homework read-only view
        App.tsx                   ← React Router (4 routes)
      vite.config.ts              ← Proxy /api and /ws to :8000 in dev mode
```

Data source: `output/*.json` files (file-based, no database).  
Pipeline modules (`agents/`) imported directly into FastAPI — no subprocess.

---

## Pages

| Route | Page | Data Source |
|-------|------|-------------|
| `/` | Student Profile | `output/student_context.json` — summary, skill breakdown, pronunciation avg, free speaking stats |
| `/lessons` | Lesson List | `output/questions_export.json` — 50 lessons, title, level, last activity date |
| `/generate` | Generate Homework | WebSocket `/ws/generate` — runs pipeline, streams progress + tokens |
| `/homework` | Homework Result | `output/homework_assignment.json` + `output/diagnostic_output.txt` |

---

## WebSocket Streaming Protocol

Endpoint: `WS /ws/generate`

Message types emitted by server (JSON):

```json
{"type": "step",  "text": "Đang tải dữ liệu..."}
{"type": "step",  "text": "[1/3] Đang phân tích học sinh..."}
{"type": "step",  "text": "[2/3] Đang chạy diagnostic agent..."}
{"type": "token", "text": "The student's performance..."}   // streamed per-token from GPT
{"type": "step",  "text": "[3/3] Đang chọn câu hỏi..."}
{"type": "done",  "homework": [...], "diagnostic": "...full text..."}
{"type": "error", "text": "...message..."}                  // on failure
```

Pipeline runs in `asyncio.run_in_executor` to avoid blocking the event loop. The diagnostic agent uses OpenAI `stream=True` and forwards each token chunk over the WebSocket. Frontend renders step messages as a progress log and token messages as a live text stream; on `done` it transitions to the result view.

---

## Error Handling

- `OPENAI_API_KEY` not set → emit `error` immediately on WebSocket connect
- Pipeline exception mid-run → emit `error` with message, close WebSocket
- `output/*.json` missing → REST endpoints return HTTP 404 with message directing user to run `preprocess.py` / `export_questions.py`
- Frontend shows error state with a "Thử lại" (retry) button

---

## Dev Workflow

```bash
# Development (two terminals)
cd web/backend && uvicorn main:app --reload --port 8000
cd web/frontend && npm run dev     # Vite :5173, proxies /api and /ws → :8000

# Local "production"
cd web/frontend && npm run build   # outputs to web/frontend/dist/
uvicorn web.backend.main:app --port 8000   # FastAPI serves dist/ as static files
```

---

## Dependencies

**Backend additions** (add to `requirements.txt`):
- `fastapi>=0.110`
- `uvicorn[standard]>=0.29`
- `websockets>=12.0`

**Frontend** (new `web/frontend/`):
- React 18 + Vite
- React Router v6
- Tailwind CSS
