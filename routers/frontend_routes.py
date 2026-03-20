from pathlib import Path
import hmac

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session

from services import read_service, share_page_service


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
FRONTEND_FILE = STATIC_DIR / "app.html"
FAVICON_FILE = STATIC_DIR / "favicon.ico"
FAVICON_FALLBACK_FILE = STATIC_DIR / "heigo.jpeg"


def _verify_internal_share_access(
    request: Request,
    *,
    expected_token: str,
    header_name: str,
) -> None:
    if not expected_token:
        return

    provided_token = (request.headers.get(header_name) or "").strip()
    if hmac.compare_digest(provided_token, expected_token):
        return

    raise HTTPException(status_code=403, detail="internal_share_token_required")


def build_frontend_router(
    get_db,
    *,
    internal_share_token: str = "",
    internal_share_header_name: str = "X-Internal-Share-Token",
):
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

    @router.get("/internal/share/player/{uid}", response_class=HTMLResponse)
    def read_internal_player_share_page(
        request: Request,
        uid: int,
        version: str | None = Query(default=None),
        step: int = Query(default=0, ge=0, le=5),
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        db: Session = Depends(get_db),
    ):
        _verify_internal_share_access(
            request,
            expected_token=internal_share_token,
            header_name=internal_share_header_name,
        )

        player = read_service.get_player_attribute_detail(db, uid, data_version=version)
        if not player:
            return HTMLResponse(
                content=(
                    "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
                    "<title>球员不存在</title></head><body>"
                    f"<h1>未找到 UID {uid} 的球员详情</h1>"
                    "</body></html>"
                ),
                status_code=404,
            )

        html = share_page_service.build_player_share_page_html(
            player,
            version=version or player.data_version,
            step=step,
            theme=theme,
        )
        return HTMLResponse(content=html)

    return router
