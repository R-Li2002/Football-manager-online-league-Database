from pathlib import Path
import hmac

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session

from services import read_service, share_page_service, share_png_service, share_signature_service, share_svg_renderer


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
PROJECT_ROOT = STATIC_DIR.parent
FRONTEND_FILE = STATIC_DIR / "app.html"
UPDATES_FILE = STATIC_DIR / "updates.html"
DATA_FEEDBACK_FILE = STATIC_DIR / "data-feedback.html"
FAVICON_FILE = STATIC_DIR / "favicon.ico"
FAVICON_FALLBACK_FILE = STATIC_DIR / "heigo.jpeg"
VERSION_FILE = PROJECT_ROOT / "VERSION"
STATIC_ASSET_VERSION_PLACEHOLDER = "__STATIC_ASSET_VERSION__"


def _load_static_asset_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        version = ""
    return version or "dev"


STATIC_ASSET_VERSION = _load_static_asset_version()


def _render_frontend_file(file_path: Path) -> str:
    html = file_path.read_text(encoding="utf-8-sig")
    return html.replace(STATIC_ASSET_VERSION_PLACEHOLDER, STATIC_ASSET_VERSION)


def _verify_internal_share_access(
    request: Request,
    *,
    expected_token: str,
    header_name: str,
) -> None:
    if not expected_token:
        raise HTTPException(status_code=503, detail="internal_share_not_configured")

    provided_token = (request.headers.get(header_name) or "").strip()
    if hmac.compare_digest(provided_token, expected_token):
        return

    raise HTTPException(status_code=403, detail="internal_share_token_required")


def _raise_signature_error(detail: str) -> None:
    if detail == "render_url_expired":
        raise HTTPException(status_code=410, detail=detail)
    if detail == "internal_render_not_configured":
        raise HTTPException(status_code=503, detail=detail)
    raise HTTPException(status_code=403, detail=detail)


def _build_png_file_response(rendered: share_png_service.RenderedSharePng) -> FileResponse:
    return FileResponse(
        rendered.file_path,
        media_type="image/png",
        filename=rendered.file_name,
        headers={
            "Cache-Control": "private, max-age=60",
            "ETag": rendered.etag,
            "X-Render-Cache": rendered.cache_status,
        },
    )


def build_frontend_router(
    get_db,
    *,
    internal_share_token: str = "",
    internal_share_header_name: str = "X-Internal-Share-Token",
    internal_render_signing_key: str = "",
    share_cache_root: str | Path = Path("data/share-cache"),
    share_template_version: int = 3,
):
    router = APIRouter()
    png_renderer = share_png_service.SharePngRenderer(
        share_cache_root,
        template_version=share_template_version,
    )

    @router.get("/", response_class=HTMLResponse)
    def read_root():
        return HTMLResponse(content=_render_frontend_file(FRONTEND_FILE))

    @router.get("/updates", response_class=FileResponse)
    def read_updates_page():
        return FileResponse(UPDATES_FILE, media_type="text/html; charset=utf-8")

    @router.get("/data-feedback", response_class=FileResponse)
    def read_data_feedback_page():
        return FileResponse(DATA_FEEDBACK_FILE, media_type="text/html; charset=utf-8")

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

    @router.get("/internal/render/player/{uid}.svg")
    def read_internal_player_share_svg(
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
            raise HTTPException(status_code=404, detail="player_not_found")

        svg = share_page_service.build_player_share_svg(
            player,
            version=version or player.data_version,
            step=step,
            theme=theme,
        )
        return Response(content=svg, media_type="image/svg+xml")

    @router.get("/internal/render/player/{uid}.png", response_class=FileResponse)
    def read_internal_player_share_png(
        uid: int,
        version: str | None = Query(default=None),
        step: int = Query(default=0, ge=0, le=5),
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        exp: int = Query(...),
        sig: str = Query(...),
        db: Session = Depends(get_db),
    ):
        validation = share_signature_service.validate_player_render_signature(
            internal_render_signing_key,
            uid=uid,
            version=version,
            step=step,
            theme=theme,
            exp=exp,
            provided_signature=sig,
        )
        if not validation.ok:
            _raise_signature_error(validation.detail)

        player = read_service.get_player_attribute_detail(db, uid, data_version=version)
        if not player:
            raise HTTPException(status_code=404, detail="player_not_found")

        try:
            rendered = png_renderer.render_player_png(
                player,
                version=version or player.data_version,
                step=step,
                theme=theme,
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"player_render_failed:{type(exc).__name__}") from exc

        return _build_png_file_response(rendered)

    @router.get("/internal/render/wage/{uid}.svg")
    def read_internal_wage_share_svg(
        request: Request,
        uid: int,
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        db: Session = Depends(get_db),
    ):
        _verify_internal_share_access(
            request,
            expected_token=internal_share_token,
            header_name=internal_share_header_name,
        )

        player = read_service.get_player_attribute_detail(db, uid)
        if not player:
            raise HTTPException(status_code=404, detail="player_not_found")
        wage_detail = read_service.get_player_wage_detail(db, uid)
        svg = share_svg_renderer.build_wage_share_svg(player, wage_detail, theme=theme)
        return Response(content=svg, media_type="image/svg+xml")

    @router.get("/internal/render/wage/{uid}.png", response_class=FileResponse)
    def read_internal_wage_share_png(
        uid: int,
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        exp: int = Query(...),
        sig: str = Query(...),
        db: Session = Depends(get_db),
    ):
        validation = share_signature_service.validate_wage_render_signature(
            internal_render_signing_key,
            uid=uid,
            theme=theme,
            exp=exp,
            provided_signature=sig,
        )
        if not validation.ok:
            _raise_signature_error(validation.detail)

        player = read_service.get_player_attribute_detail(db, uid)
        if not player:
            raise HTTPException(status_code=404, detail="player_not_found")
        wage_detail = read_service.get_player_wage_detail(db, uid)
        try:
            rendered = png_renderer.render_wage_png(player, wage_detail, theme=theme)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"wage_render_failed:{type(exc).__name__}") from exc
        return _build_png_file_response(rendered)

    @router.get("/internal/render/roster.svg")
    def read_internal_roster_share_svg(
        request: Request,
        team: str = Query(..., min_length=1),
        page: int = Query(default=1, ge=1, le=20),
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        db: Session = Depends(get_db),
    ):
        _verify_internal_share_access(
            request,
            expected_token=internal_share_token,
            header_name=internal_share_header_name,
        )

        players = read_service.get_players_by_team(db, team)
        if not players:
            raise HTTPException(status_code=404, detail="team_not_found")
        try:
            team_info = read_service.get_team_info(db, team)
        except HTTPException:
            team_info = None
        svg = share_svg_renderer.build_roster_share_svg(
            team,
            players,
            team_info=team_info,
            page=page,
            theme=theme,
        )
        return Response(content=svg, media_type="image/svg+xml")

    @router.get("/internal/render/roster.png", response_class=FileResponse)
    def read_internal_roster_share_png(
        team: str = Query(..., min_length=1),
        page: int = Query(default=1, ge=1, le=20),
        theme: str = Query(default="dark", pattern="^(dark|light)$"),
        exp: int = Query(...),
        sig: str = Query(...),
        db: Session = Depends(get_db),
    ):
        validation = share_signature_service.validate_roster_render_signature(
            internal_render_signing_key,
            team_name=team,
            page=page,
            theme=theme,
            exp=exp,
            provided_signature=sig,
        )
        if not validation.ok:
            _raise_signature_error(validation.detail)

        players = read_service.get_players_by_team(db, team)
        if not players:
            raise HTTPException(status_code=404, detail="team_not_found")
        try:
            team_info = read_service.get_team_info(db, team)
        except HTTPException:
            team_info = None
        try:
            rendered = png_renderer.render_roster_png(
                team,
                players,
                team_info=team_info,
                page=page,
                theme=theme,
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"roster_render_failed:{type(exc).__name__}") from exc
        return _build_png_file_response(rendered)

    return router
