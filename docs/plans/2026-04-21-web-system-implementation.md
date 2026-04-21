# Web System (FastAPI + React) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local web UI with FastAPI backend and React/Vite frontend that exposes student profile, lesson list, and the homework generation pipeline with WebSocket streaming.

**Architecture:** FastAPI serves REST API + WebSocket at port 8000; in dev mode Vite proxies `/api` and `/ws` to backend; in production FastAPI serves the built `dist/` as static files. Pipeline agents are imported directly into the FastAPI process and the diagnostic step uses `AsyncOpenAI` for token-level streaming over WebSocket.

**Tech Stack:** Python 3.12, FastAPI 0.110+, uvicorn, React 18, Vite, React Router v6, Tailwind CSS, AsyncOpenAI

---

## Prerequisites

From project root `/home/pc600/Desktop/phase-0-learning-flow`:
- `output/student_context.json` exists (run `python preprocess.py` if not)
- `output/questions_export.json` exists (run `python export_questions.py` if not)

Install new backend deps:
```bash
pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" websockets
```

---

## Task 1: Backend scaffold

**Files:**
- Create: `web/__init__.py`
- Create: `web/backend/__init__.py`
- Create: `web/backend/main.py`

**Step 1: Create package init files**

```bash
mkdir -p web/backend/routers
touch web/__init__.py web/backend/__init__.py web/backend/routers/__init__.py
```

**Step 2: Write `web/backend/main.py`**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.backend.routers import student, lessons, homework

app = FastAPI(title="Phase 0 Learning Flow")

app.include_router(student.router)
app.include_router(lessons.router)
app.include_router(homework.router)

dist = Path(__file__).parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
```

**Step 3: Verify import works**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
python -c "from web.backend.main import app; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add web/
git commit -m "feat: add FastAPI backend scaffold"
```

---

## Task 2: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Write updated requirements**

```
openai>=1.30
pytest>=8.0
fastapi>=0.110
uvicorn[standard]>=0.29
websockets>=12.0
httpx>=0.27
```

(`httpx` is needed for FastAPI TestClient.)

**Step 2: Install**

```bash
pip install -r requirements.txt
```

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add fastapi/uvicorn/websockets/httpx deps"
```

---

## Task 3: Student API router

**Files:**
- Create: `web/backend/routers/student.py`
- Create: `tests/test_student_api.py`

**Step 1: Write failing test**

```python
# tests/test_student_api.py
import json
from pathlib import Path
from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)

def test_get_student_returns_summary(tmp_path, monkeypatch):
    data = {
        "summary": {
            "student_id": 2102555,
            "total_lessons": 50,
            "overall_pronunciation_score_avg": 86.96,
            "overall_free_speaking_score_avg": 30.71,
            "overall_homework_skill_breakdown": {},
            "lessons_by_status": {"completed": 48},
            "overall_free_speaking_answer_type_dist": {},
            "weak_skills_global": [],
        }
    }
    f = tmp_path / "student_context.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.student.STUDENT_CONTEXT_PATH", str(f))
    resp = client.get("/api/student")
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_id"] == 2102555
    assert body["total_lessons"] == 50

def test_get_student_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.student.STUDENT_CONTEXT_PATH",
        str(tmp_path / "missing.json"),
    )
    resp = client.get("/api/student")
    assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_student_api.py -v
```

Expected: FAIL — `web/backend/routers/student.py` does not exist yet.

**Step 3: Write `web/backend/routers/student.py`**

```python
from pathlib import Path

from fastapi import APIRouter, HTTPException

STUDENT_CONTEXT_PATH = "output/student_context.json"

router = APIRouter(prefix="/api")


@router.get("/student")
def get_student():
    import json
    p = Path(STUDENT_CONTEXT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="student_context.json not found — run preprocess.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["summary"]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_student_api.py -v
```

Expected: 2 PASSED

**Step 5: Commit**

```bash
git add web/backend/routers/student.py tests/test_student_api.py
git commit -m "feat: add GET /api/student endpoint"
```

---

## Task 4: Lessons API router

**Files:**
- Create: `web/backend/routers/lessons.py`
- Create: `tests/test_lessons_api.py`

**Step 1: Write failing test**

```python
# tests/test_lessons_api.py
import json
from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)

def test_get_lessons_returns_list(tmp_path, monkeypatch):
    data = {
        "lessons": [
            {"lesson_id": 1, "title": "Unit 1", "level": 5,
             "last_activity_date": "2026-04-15", "position": 1, "desc": "desc"},
            {"lesson_id": 2, "title": "Unit 2", "level": 4,
             "last_activity_date": "2026-04-10", "position": 2, "desc": ""},
        ]
    }
    f = tmp_path / "questions_export.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.lessons.QUESTIONS_EXPORT_PATH", str(f))
    resp = client.get("/api/lessons")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["lesson_id"] == 1

def test_get_lessons_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.lessons.QUESTIONS_EXPORT_PATH",
        str(tmp_path / "missing.json"),
    )
    resp = client.get("/api/lessons")
    assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_lessons_api.py -v
```

Expected: FAIL

**Step 3: Write `web/backend/routers/lessons.py`**

```python
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

QUESTIONS_EXPORT_PATH = "output/questions_export.json"

router = APIRouter(prefix="/api")


@router.get("/lessons")
def get_lessons():
    p = Path(QUESTIONS_EXPORT_PATH)
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail="questions_export.json not found — run export_questions.py first",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return [
        {
            "lesson_id": l["lesson_id"],
            "title": l["title"],
            "level": l.get("level"),
            "position": l.get("position"),
            "last_activity_date": l.get("last_activity_date"),
            "desc": l.get("desc", ""),
        }
        for l in data.get("lessons", [])
    ]
```

**Step 4: Run tests**

```bash
pytest tests/test_lessons_api.py -v
```

Expected: 2 PASSED

**Step 5: Commit**

```bash
git add web/backend/routers/lessons.py tests/test_lessons_api.py
git commit -m "feat: add GET /api/lessons endpoint"
```

---

## Task 5: Homework GET API router

**Files:**
- Create: `web/backend/routers/homework.py`
- Create: `tests/test_homework_api.py`

**Step 1: Write failing test**

```python
# tests/test_homework_api.py
import json
from fastapi.testclient import TestClient
from web.backend.main import app

client = TestClient(app)

def test_get_homework_returns_data(tmp_path, monkeypatch):
    hw = {"homework": [{"question_no": 1, "lesson_id": 100,
                         "lesson_title": "T", "skill_category": "grammar",
                         "question_type": "fill", "question_text": "Q",
                         "correct_answer": "A", "difficulty": "easy",
                         "reason": "R"}]}
    diag = "Student analysis text."
    hw_file = tmp_path / "homework_assignment.json"
    hw_file.write_text(json.dumps(hw), encoding="utf-8")
    diag_file = tmp_path / "diagnostic_output.txt"
    diag_file.write_text(diag, encoding="utf-8")
    monkeypatch.setattr("web.backend.routers.homework.HOMEWORK_PATH", str(hw_file))
    monkeypatch.setattr("web.backend.routers.homework.DIAGNOSTIC_PATH", str(diag_file))
    resp = client.get("/api/homework")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["homework"]) == 1
    assert body["diagnostic"] == diag

def test_get_homework_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web.backend.routers.homework.HOMEWORK_PATH",
        str(tmp_path / "missing.json"),
    )
    monkeypatch.setattr(
        "web.backend.routers.homework.DIAGNOSTIC_PATH",
        str(tmp_path / "missing.txt"),
    )
    resp = client.get("/api/homework")
    assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_homework_api.py -v
```

Expected: FAIL

**Step 3: Write `web/backend/routers/homework.py`** (GET only for now, WS added in Task 6)

```python
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
```

**Step 4: Run tests**

```bash
pytest tests/test_homework_api.py -v
```

Expected: 2 PASSED

**Step 5: Run all tests to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all pass

**Step 6: Commit**

```bash
git add web/backend/routers/homework.py tests/test_homework_api.py
git commit -m "feat: add GET /api/homework endpoint"
```

---

## Task 6: WebSocket pipeline endpoint

**Files:**
- Create: `web/backend/pipeline_ws.py`
- Modify: `web/backend/routers/homework.py` (add WS route)

**Context:** The WebSocket handler runs context_builder in a thread, then streams diagnostic tokens via `AsyncOpenAI`, then runs selector in a thread. An `asyncio.Queue` passes step-log messages from threads back to the async handler.

**Step 1: Create `web/backend/pipeline_ws.py`**

```python
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

STUDENT_CONTEXT_PATH = "output/student_context.json"
QUESTIONS_EXPORT_PATH = "output/questions_export.json"
HOMEWORK_PATH = "output/homework_assignment.json"
DIAGNOSTIC_PATH = "output/diagnostic_output.txt"


async def run_pipeline_ws(send) -> None:
    """
    send: async callable that accepts a dict and sends it as JSON over WebSocket.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        await send({"type": "error", "text": "OPENAI_API_KEY chưa được cấu hình"})
        return

    for path in (STUDENT_CONTEXT_PATH, QUESTIONS_EXPORT_PATH):
        if not Path(path).exists():
            await send({"type": "error", "text": f"{path} không tồn tại — chạy preprocess.py trước"})
            return

    await send({"type": "step", "text": "Đang tải dữ liệu..."})

    loop = asyncio.get_event_loop()

    def _load():
        import json as _json
        sc = _json.loads(Path(STUDENT_CONTEXT_PATH).read_text(encoding="utf-8"))
        qe = _json.loads(Path(QUESTIONS_EXPORT_PATH).read_text(encoding="utf-8"))
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

    from agents.diagnostic_agent import build_prompt, SYSTEM_PROMPT

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
```

**Step 2: Add WebSocket route to `web/backend/routers/homework.py`**

Add at the bottom of the existing file:

```python
from fastapi import WebSocket, WebSocketDisconnect
from web.backend.pipeline_ws import run_pipeline_ws


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
```

Note: The `router` prefix is `/api` but WebSocket routes use the full path. Change the websocket decorator to use the path without the `/api` prefix by using a separate router or adjusting the mount. Since `APIRouter(prefix="/api")` applies to HTTP routes, add a note: FastAPI applies the prefix to WebSocket routes too, so the final path will be `/api/ws/generate`. Update the frontend accordingly.

**Step 3: Verify the backend starts**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
uvicorn web.backend.main:app --port 8000 --reload
```

Expected: server starts, no import errors. Press Ctrl+C.

**Step 4: Commit**

```bash
git add web/backend/pipeline_ws.py web/backend/routers/homework.py
git commit -m "feat: add WebSocket /api/ws/generate with streaming pipeline"
```

---

## Task 7: Frontend scaffold

**Files:**
- Create: `web/frontend/` (Vite React project)

**Step 1: Scaffold with Vite**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow/web
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom
npm install -D tailwindcss @tailwindcss/vite
```

**Step 2: Configure Tailwind — update `web/frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

**Step 3: Add Tailwind import to `web/frontend/src/index.css`**

Replace entire file with:
```css
@import "tailwindcss";
```

**Step 4: Verify frontend builds**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow/web/frontend
npm run build
```

Expected: `dist/` created, no errors.

**Step 5: Commit**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
git add web/frontend/
git commit -m "feat: scaffold React/Vite/Tailwind frontend"
```

---

## Task 8: App shell and routing

**Files:**
- Modify: `web/frontend/src/main.tsx`
- Modify: `web/frontend/src/App.tsx`
- Create: `web/frontend/src/pages/StudentProfile.tsx`
- Create: `web/frontend/src/pages/LessonList.tsx`
- Create: `web/frontend/src/pages/GenerateHomework.tsx`
- Create: `web/frontend/src/pages/HomeworkResult.tsx`

**Step 1: Update `web/frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

**Step 2: Write `web/frontend/src/App.tsx`**

```tsx
import { Routes, Route, NavLink } from 'react-router-dom'
import StudentProfile from './pages/StudentProfile'
import LessonList from './pages/LessonList'
import GenerateHomework from './pages/GenerateHomework'
import HomeworkResult from './pages/HomeworkResult'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
  }`

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex gap-2 items-center">
        <span className="text-blue-400 font-bold mr-4">Phase 0</span>
        <NavLink to="/" end className={navClass}>Học sinh</NavLink>
        <NavLink to="/lessons" className={navClass}>Bài học</NavLink>
        <NavLink to="/generate" className={navClass}>Tạo bài tập</NavLink>
        <NavLink to="/homework" className={navClass}>Kết quả</NavLink>
      </nav>
      <main className="max-w-5xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<StudentProfile />} />
          <Route path="/lessons" element={<LessonList />} />
          <Route path="/generate" element={<GenerateHomework />} />
          <Route path="/homework" element={<HomeworkResult />} />
        </Routes>
      </main>
    </div>
  )
}
```

**Step 3: Create stub pages** (one each, replace in later tasks)

`web/frontend/src/pages/StudentProfile.tsx`:
```tsx
export default function StudentProfile() { return <div>Student Profile</div> }
```

`web/frontend/src/pages/LessonList.tsx`:
```tsx
export default function LessonList() { return <div>Lesson List</div> }
```

`web/frontend/src/pages/GenerateHomework.tsx`:
```tsx
export default function GenerateHomework() { return <div>Generate Homework</div> }
```

`web/frontend/src/pages/HomeworkResult.tsx`:
```tsx
export default function HomeworkResult() { return <div>Homework Result</div> }
```

**Step 4: Verify dev server runs**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow/web/frontend
npm run dev
```

Open http://localhost:5173 — should see nav bar with 4 links. Press Ctrl+C.

**Step 5: Commit**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
git add web/frontend/src/
git commit -m "feat: add React Router shell with 4-page nav"
```

---

## Task 9: StudentProfile page

**Files:**
- Modify: `web/frontend/src/pages/StudentProfile.tsx`

API shape from `GET /api/student`:
```json
{
  "student_id": 2102555,
  "total_lessons": 50,
  "overall_pronunciation_score_avg": 86.96,
  "overall_free_speaking_score_avg": 30.71,
  "overall_homework_skill_breakdown": { "English Tutoring - Level 5": { "correct": 1109, "total": 1178, "accuracy": 0.941 } },
  "lessons_by_status": { "completed": 48, "in_class_only": 2 },
  "overall_free_speaking_answer_type_dist": { "correct": 48, "incorrect": 34, ... },
  "weak_skills_global": []
}
```

**Step 1: Write `web/frontend/src/pages/StudentProfile.tsx`**

```tsx
import { useEffect, useState } from 'react'

interface StudentSummary {
  student_id: number
  total_lessons: number
  overall_pronunciation_score_avg: number
  overall_free_speaking_score_avg: number
  overall_homework_skill_breakdown: Record<string, { correct: number; total: number; accuracy: number }>
  lessons_by_status: Record<string, number>
  overall_free_speaking_answer_type_dist: Record<string, number>
  weak_skills_global: string[]
}

export default function StudentProfile() {
  const [data, setData] = useState<StudentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/student')
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(setData)
      .catch(e => setError(String(e)))
  }, [])

  if (error) return <p className="text-red-400">{error}</p>
  if (!data) return <p className="text-gray-400">Đang tải...</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Học sinh #{data.student_id}</h1>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Tổng bài học" value={data.total_lessons} />
        <StatCard label="Đã hoàn thành" value={data.lessons_by_status['completed'] ?? 0} />
        <StatCard label="Phát âm TB" value={`${data.overall_pronunciation_score_avg.toFixed(1)}/100`} />
        <StatCard label="Nói tự do TB" value={`${data.overall_free_speaking_score_avg.toFixed(1)}/100`} />
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">Kỹ năng theo chủ đề</h2>
        <div className="space-y-2">
          {Object.entries(data.overall_homework_skill_breakdown).map(([skill, stats]) => (
            <div key={skill} className="bg-gray-800 rounded-lg p-3">
              <div className="flex justify-between text-sm mb-1">
                <span>{skill}</span>
                <span className="text-gray-400">{stats.correct}/{stats.total} ({(stats.accuracy * 100).toFixed(0)}%)</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${stats.accuracy * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Phân bố câu trả lời nói tự do</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.overall_free_speaking_answer_type_dist).map(([type, count]) => (
            <span key={type} className="bg-gray-800 px-3 py-1 rounded-full text-sm">
              {type}: <strong>{count}</strong>
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}
```

**Step 2: Start dev servers and verify in browser**

Terminal 1:
```bash
cd /home/pc600/Desktop/phase-0-learning-flow
uvicorn web.backend.main:app --port 8000 --reload
```
Terminal 2:
```bash
cd /home/pc600/Desktop/phase-0-learning-flow/web/frontend
npm run dev
```

Open http://localhost:5173 — should see student profile with stats and skill bars.

**Step 3: Commit**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
git add web/frontend/src/pages/StudentProfile.tsx
git commit -m "feat: StudentProfile page with skill breakdown"
```

---

## Task 10: LessonList page

**Files:**
- Modify: `web/frontend/src/pages/LessonList.tsx`

API shape from `GET /api/lessons` — array of:
```json
{ "lesson_id": 1, "title": "...", "level": 5, "position": 1, "last_activity_date": "2026-04-15", "desc": "..." }
```

**Step 1: Write `web/frontend/src/pages/LessonList.tsx`**

```tsx
import { useEffect, useState } from 'react'

interface Lesson {
  lesson_id: number
  title: string
  level: number | null
  position: number | null
  last_activity_date: string | null
  desc: string
}

export default function LessonList() {
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/lessons')
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(setLessons)
      .catch(e => setError(String(e)))
  }, [])

  if (error) return <p className="text-red-400">{error}</p>
  if (!lessons.length) return <p className="text-gray-400">Đang tải...</p>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Danh sách bài học ({lessons.length})</h1>
      <div className="space-y-2">
        {lessons.map(l => (
          <div key={l.lesson_id} className="bg-gray-800 rounded-xl p-4 flex justify-between items-start">
            <div>
              <p className="font-medium">{l.title}</p>
              {l.desc && <p className="text-gray-400 text-sm mt-1 line-clamp-2">{l.desc}</p>}
            </div>
            <div className="text-right text-sm shrink-0 ml-4">
              {l.level && <span className="bg-blue-900 text-blue-200 px-2 py-0.5 rounded mr-2">Lv.{l.level}</span>}
              {l.last_activity_date && (
                <span className="text-gray-400">{l.last_activity_date}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Verify in browser** at http://localhost:5173/lessons — 50 lessons listed.

**Step 3: Commit**

```bash
git add web/frontend/src/pages/LessonList.tsx
git commit -m "feat: LessonList page"
```

---

## Task 11: GenerateHomework page with WebSocket streaming

**Files:**
- Modify: `web/frontend/src/pages/GenerateHomework.tsx`

WebSocket endpoint: `ws://localhost:8000/api/ws/generate` (in dev, Vite proxies `/ws` → `:8000`; but since path starts with `/api/ws`, the `/api` proxy handles it as HTTP — need to use the WebSocket URL directly in dev or adjust proxy).

**Note on proxy:** Vite's proxy config uses string match on the path prefix. `/api` proxy is HTTP-only. For WebSocket at `/api/ws/generate`, add a specific WebSocket proxy entry:

Update `web/frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api/ws': { target: 'ws://localhost:8000', ws: true },
      '/api': 'http://localhost:8000',
    },
  },
})
```

(The `/api/ws` entry must come before `/api` so it matches first.)

**Step 1: Write `web/frontend/src/pages/GenerateHomework.tsx`**

```tsx
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type WsMsg =
  | { type: 'step'; text: string }
  | { type: 'token'; text: string }
  | { type: 'done'; homework: unknown[]; diagnostic: string }
  | { type: 'error'; text: string }

export default function GenerateHomework() {
  const [steps, setSteps] = useState<string[]>([])
  const [diagnostic, setDiagnostic] = useState('')
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const navigate = useNavigate()

  function start() {
    setSteps([])
    setDiagnostic('')
    setErrorMsg('')
    setStatus('running')

    const ws = new WebSocket(`ws://${location.host}/api/ws/generate`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg: WsMsg = JSON.parse(e.data)
      if (msg.type === 'step') {
        setSteps(s => [...s, msg.text])
      } else if (msg.type === 'token') {
        setDiagnostic(d => d + msg.text)
      } else if (msg.type === 'done') {
        setStatus('done')
      } else if (msg.type === 'error') {
        setErrorMsg(msg.text)
        setStatus('error')
      }
    }

    ws.onerror = () => {
      setErrorMsg('Kết nối WebSocket thất bại')
      setStatus('error')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tạo bài tập về nhà</h1>

      {status === 'idle' && (
        <button
          onClick={start}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-medium transition-colors"
        >
          Bắt đầu tạo bài tập
        </button>
      )}

      {status === 'running' && (
        <button disabled className="bg-gray-700 text-gray-400 px-6 py-3 rounded-xl font-medium cursor-not-allowed">
          Đang tạo...
        </button>
      )}

      {steps.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-4 space-y-1">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Tiến trình</p>
          {steps.map((s, i) => (
            <p key={i} className="text-sm font-mono text-green-400">▶ {s}</p>
          ))}
        </div>
      )}

      {diagnostic && (
        <div className="bg-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Phân tích học sinh</p>
          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{diagnostic}</p>
        </div>
      )}

      {status === 'error' && (
        <div className="bg-red-900/40 border border-red-700 rounded-xl p-4">
          <p className="text-red-300">{errorMsg}</p>
          <button
            onClick={() => setStatus('idle')}
            className="mt-3 text-sm text-red-400 underline"
          >
            Thử lại
          </button>
        </div>
      )}

      {status === 'done' && (
        <div className="bg-green-900/40 border border-green-700 rounded-xl p-4">
          <p className="text-green-300 font-medium">Tạo bài tập thành công!</p>
          <button
            onClick={() => navigate('/homework')}
            className="mt-3 bg-green-700 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
          >
            Xem bài tập →
          </button>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser** at http://localhost:5173/generate — click "Bắt đầu tạo bài tập", confirm steps appear and diagnostic streams.

**Step 3: Commit**

```bash
git add web/frontend/src/pages/GenerateHomework.tsx web/frontend/vite.config.ts
git commit -m "feat: GenerateHomework page with WebSocket streaming"
```

---

## Task 12: HomeworkResult page

**Files:**
- Modify: `web/frontend/src/pages/HomeworkResult.tsx`

API shape from `GET /api/homework`:
```json
{
  "homework": [{ "question_no": 1, "lesson_title": "...", "skill_category": "grammar",
                 "question_type": "...", "question_text": "...", "correct_answer": "...",
                 "difficulty": "easy", "reason": "..." }],
  "diagnostic": "Full diagnostic text..."
}
```

**Step 1: Write `web/frontend/src/pages/HomeworkResult.tsx`**

```tsx
import { useEffect, useState } from 'react'

interface Question {
  question_no: number
  lesson_title: string
  skill_category: string
  question_type: string
  question_text: string
  correct_answer: string | null
  difficulty: 'easy' | 'medium' | 'hard'
  reason: string
}

interface HomeworkData {
  homework: Question[]
  diagnostic: string
}

const difficultyColor = {
  easy: 'bg-green-900 text-green-300',
  medium: 'bg-yellow-900 text-yellow-300',
  hard: 'bg-red-900 text-red-300',
}

const skillColor: Record<string, string> = {
  grammar: 'bg-blue-900 text-blue-300',
  vocabulary: 'bg-purple-900 text-purple-300',
  speaking: 'bg-orange-900 text-orange-300',
  pronunciation: 'bg-pink-900 text-pink-300',
  other: 'bg-gray-700 text-gray-300',
}

export default function HomeworkResult() {
  const [data, setData] = useState<HomeworkData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDiag, setShowDiag] = useState(false)

  useEffect(() => {
    fetch('/api/homework')
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(setData)
      .catch(e => setError(String(e)))
  }, [])

  if (error) return (
    <div className="space-y-3">
      <p className="text-red-400">{error}</p>
      <a href="/generate" className="text-blue-400 underline text-sm">Tạo bài tập mới</a>
    </div>
  )
  if (!data) return <p className="text-gray-400">Đang tải...</p>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Bài tập về nhà ({data.homework.length} câu)</h1>
        <button
          onClick={() => setShowDiag(d => !d)}
          className="text-sm text-gray-400 underline"
        >
          {showDiag ? 'Ẩn' : 'Xem'} đánh giá
        </button>
      </div>

      {showDiag && (
        <div className="bg-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Đánh giá học sinh</p>
          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{data.diagnostic}</p>
        </div>
      )}

      <div className="space-y-3">
        {data.homework.map(q => (
          <div key={q.question_no} className="bg-gray-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <span className="text-gray-500 font-mono text-sm w-6 shrink-0">{q.question_no}.</span>
              <div className="flex-1 space-y-2">
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className={`px-2 py-0.5 rounded ${skillColor[q.skill_category] ?? skillColor.other}`}>
                    {q.skill_category}
                  </span>
                  <span className={`px-2 py-0.5 rounded ${difficultyColor[q.difficulty]}`}>
                    {q.difficulty}
                  </span>
                  <span className="bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{q.question_type}</span>
                </div>
                <p className="text-xs text-gray-400">{q.lesson_title}</p>
                <p className="text-sm">{q.question_text}</p>
                {q.correct_answer && (
                  <p className="text-xs text-green-400">Đáp án: {q.correct_answer}</p>
                )}
                <p className="text-xs text-gray-400 italic">{q.reason}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Verify in browser** at http://localhost:5173/homework — should see 15 homework questions with tags, answers, and reasoning.

**Step 3: Commit**

```bash
git add web/frontend/src/pages/HomeworkResult.tsx
git commit -m "feat: HomeworkResult page with diagnostic toggle"
```

---

## Task 13: Production build verification

**Step 1: Build frontend**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow/web/frontend
npm run build
```

Expected: `dist/` created with `index.html` and assets.

**Step 2: Start single server**

```bash
cd /home/pc600/Desktop/phase-0-learning-flow
uvicorn web.backend.main:app --port 8000
```

**Step 3: Verify all pages at http://localhost:8000**

- http://localhost:8000/ → Student profile loads
- http://localhost:8000/lessons → 50 lessons
- http://localhost:8000/generate → Pipeline UI
- http://localhost:8000/homework → Homework list

**Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete web system — FastAPI + React with WebSocket pipeline streaming"
```
