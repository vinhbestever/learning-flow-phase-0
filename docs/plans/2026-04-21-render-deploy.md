# Render Deploy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the Phase 0 Learning Flow app (FastAPI backend + React frontend) as a single service on Render.

**Architecture:** Render runs one web service — build step installs deps and compiles the Vite frontend into `dist/`, then uvicorn serves FastAPI which mounts that `dist/` as static files. Output data files (`output/*.json`, `output/*.txt`) are committed to the repo so they're available at runtime without any preprocessing step.

**Tech Stack:** Python 3, FastAPI, uvicorn, React 19, Vite, Tailwind CSS, Render (PaaS)

---

### Task 1: Un-exclude output files from .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Remove 4 lines that exclude output files**

Open `.gitignore` and delete these exact lines:
```
diagnostic_output.txt
homework_assignment.json
questions_export.json
student_context.json
```

**Step 2: Verify output files are now tracked**

```bash
git status output/
```
Expected: 4 files shown as untracked (not ignored).

**Step 3: Commit**

```bash
git add .gitignore output/student_context.json output/questions_export.json output/homework_assignment.json output/diagnostic_output.txt
git commit -m "chore: track output data files for Render deploy"
```

---

### Task 2: Create render.yaml

**Files:**
- Create: `render.yaml`

**Step 1: Create the file**

```yaml
services:
  - type: web
    name: phase-0-learning-flow
    runtime: python
    buildCommand: pip install -r requirements.txt && cd web/frontend && npm ci && npm run build
    startCommand: uvicorn web.backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
```

**Step 2: Verify FastAPI mounts dist correctly**

Check `web/backend/main.py` — it already does:
```python
dist = Path(__file__).parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
```
This resolves to `web/frontend/dist/` after the Vite build — correct.

**Step 3: Commit**

```bash
git add render.yaml
git commit -m "chore: add render.yaml for Render deployment"
```

---

### Task 3: Push to GitHub and connect to Render

**Step 1: Push to GitHub**

```bash
git push
```

**Step 2: Connect repo on Render dashboard**

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml` and pre-fill settings
4. In **Environment Variables**, add `OPENAI_API_KEY` = your key
5. Click **Create Web Service**

**Step 3: Verify build logs**

In the Render dashboard, watch the build log. Expected sequence:
```
==> Running build command: pip install -r requirements.txt && cd web/frontend && npm ci && npm run build
...
==> Build successful
==> Starting service with: uvicorn web.backend.main:app --host 0.0.0.0 --port $PORT
INFO:     Application startup complete.
```

**Step 4: Smoke test**

Open the Render-provided URL (e.g. `https://phase-0-learning-flow.onrender.com`):
- `/` → React SPA loads
- `/api/student` → returns student JSON
- `/api/lessons` → returns lesson list

---

### Notes

- Free Render tier spins down after 15 min inactivity — first request takes ~30s to wake up.
- `OPENAI_API_KEY` is set via Render dashboard (never committed to repo).
- To regenerate homework data locally: `python preprocess.py && python export_questions.py && python agent_pipeline.py`, then commit the updated `output/` files and push.
