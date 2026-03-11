from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


FRONTEND_FILE = Path(__file__).resolve().parents[1] / "static" / "app.html"


def build_frontend_router():
    router = APIRouter()

    @router.get("/", response_class=FileResponse)
    def read_root():
        return FileResponse(FRONTEND_FILE, media_type="text/html; charset=utf-8")

    return router
