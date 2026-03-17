from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
FRONTEND_FILE = STATIC_DIR / "app.html"
FAVICON_FILE = STATIC_DIR / "favicon.ico"
FAVICON_FALLBACK_FILE = STATIC_DIR / "heigo.jpeg"


def build_frontend_router():
    router = APIRouter()

    @router.get("/", response_class=FileResponse)
    def read_root():
        return FileResponse(FRONTEND_FILE, media_type="text/html; charset=utf-8")

    @router.get("/favicon.ico", include_in_schema=False)
    def read_favicon():
        if FAVICON_FILE.exists():
            return FileResponse(FAVICON_FILE, media_type="image/x-icon")
        if FAVICON_FALLBACK_FILE.exists():
            return FileResponse(FAVICON_FALLBACK_FILE, media_type="image/jpeg")
        return Response(status_code=204)

    return router
