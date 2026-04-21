from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.backend.routers import homework, lessons, student

app = FastAPI(title="Phase 0 Learning Flow")

app.include_router(student.router)
app.include_router(lessons.router)
app.include_router(homework.router)

dist = Path(__file__).parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
