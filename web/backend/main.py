from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.backend.routers import history, homework, lessons, student

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

app = FastAPI(title="Phase 0 Learning Flow")

app.include_router(student.router)
app.include_router(lessons.router)
app.include_router(history.router)
app.include_router(homework.router)

dist = Path(__file__).parent.parent / "frontend" / "dist"
if dist.exists():
    dist_resolved = dist.resolve()
    index_path = dist / "index.html"

    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="static-assets",
        )

    def _is_under_dist(path: Path) -> bool:
        try:
            path.resolve().relative_to(dist_resolved)
        except ValueError:
            return False
        return True

    @app.get("/")
    def spa_index() -> FileResponse:
        if not index_path.is_file():
            raise HTTPException(
                status_code=503, detail="Frontend dist missing index.html"
            )
        return FileResponse(index_path)

    @app.get("/{full_path:path}")
    def spa_or_file(full_path: str) -> FileResponse:
        # Unmatched /api/... should stay a JSON 404, not the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        path = (dist / full_path).resolve()
        if not _is_under_dist(path):
            raise HTTPException(status_code=404, detail="Not Found")
        if path.is_file():
            return FileResponse(path)
        if not index_path.is_file():
            raise HTTPException(
                status_code=503, detail="Frontend dist missing index.html"
            )
        return FileResponse(index_path)
