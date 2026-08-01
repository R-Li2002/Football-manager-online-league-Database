from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
import shutil
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.gzip import GZipMiddleware

from app_bootstrap import LOG_FILE, initialize_app_state, shutdown_app_state, write_to_log
from app_security import clear_session_cookie, set_session_cookie
from auth_utils import get_session_username
from database import SessionLocal, engine
from routers.admin_read_routes import build_admin_read_router
from routers.admin_write_routes import build_admin_write_router
from routers.frontend_routes import build_frontend_router
from routers.public_routes import build_public_router
from routers.workspace_routes import build_workspace_router
from services import auth_service
from services.share_cache_cleanup_service import run_share_cache_cleanup_loop

INTERNAL_SHARE_TOKEN = os.environ.get("INTERNAL_SHARE_TOKEN", "").strip()
INTERNAL_SHARE_HEADER_NAME = "X-Internal-Share-Token"
INTERNAL_RENDER_SIGNING_KEY = os.environ.get("INTERNAL_RENDER_SIGNING_KEY", "").strip()
SHARE_CACHE_ROOT = os.environ.get("HEIGO_SHARE_CACHE_ROOT", "data/share-cache").strip() or "data/share-cache"
SHARE_TEMPLATE_VERSION = int(os.environ.get("HEIGO_SHARE_TEMPLATE_VERSION", "6"))
SHARE_CACHE_RETENTION_DAYS = int(os.environ.get("HEIGO_SHARE_CACHE_RETENTION_DAYS", "30"))
COACH_SESSION_COOKIE_NAME = "coach_session_token"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_authenticated_admin(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    return get_session_username(db, session_token)


def verify_admin(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    return username if auth_service.can_manage_admin(role) else None


def verify_schedule_editor(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    return username if auth_service.can_manage_schedule(role) else None


def verify_schedule_manager(
    session_token: Optional[str] = Cookie(None),
    coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    if username and auth_service.can_manage_schedule(role):
        return username
    coach_operator = auth_service.get_coach_work_operator(db, coach_session_token, "schedule")
    if coach_operator:
        return coach_operator
    raise HTTPException(status_code=401, detail="未授权")


def verify_cup_standings_manager(
    session_token: Optional[str] = Cookie(None),
    coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    if username and auth_service.can_manage_cup_standings(role):
        return username
    coach_operator = auth_service.get_coach_work_operator(db, coach_session_token, "cup_standings")
    if coach_operator:
        return coach_operator
    raise HTTPException(status_code=401, detail="未授权")


def verify_suspension_manager(
    session_token: Optional[str] = Cookie(None),
    coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    if username and auth_service.can_manage_suspensions(role):
        return username
    coach_operator = auth_service.get_coach_work_operator(db, coach_session_token, "suspensions")
    if coach_operator:
        return coach_operator
    raise HTTPException(status_code=401, detail="未授权")


def verify_candidate_list_manager(
    session_token: Optional[str] = Cookie(None),
    coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    username = get_session_username(db, session_token)
    role = auth_service.get_admin_role(db, username)
    if username and auth_service.can_manage_candidate_lists(role):
        return username
    coach_operator = auth_service.get_coach_work_operator(db, coach_session_token, "candidate_lists")
    if coach_operator:
        return coach_operator
    raise HTTPException(status_code=401, detail="未授权")


def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "unreachable", "error": type(exc).__name__},
        ) from exc

    return {"status": "ok", "database": "ok"}


def _ensure_static_assets() -> None:
    if not os.path.exists("static"):
        os.makedirs("static")

    if os.path.exists("heigo.jpeg") and not os.path.exists("static/heigo.jpeg"):
        shutil.copy2("heigo.jpeg", "static/heigo.jpeg")

    trophy_source = "imports/trophy"
    trophy_target = "static/images/trophy"
    if os.path.isdir(trophy_source):
        os.makedirs(trophy_target, exist_ok=True)
        for filename in ("champion.png", "league.png", "FA.png"):
            source_path = os.path.join(trophy_source, filename)
            target_path = os.path.join(trophy_target, filename)
            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
                if filename in {"champion.png", "league.png"}:
                    _make_border_white_transparent(target_path)


def _make_border_white_transparent(image_path: str) -> None:
    try:
        from PIL import Image
    except ImportError:
        return

    try:
        image = Image.open(image_path).convert("RGBA")
    except OSError:
        return

    width, height = image.size
    pixels = image.load()

    def is_white_background(x: int, y: int) -> bool:
        red, green, blue, alpha = pixels[x, y]
        return alpha > 0 and red >= 245 and green >= 245 and blue >= 245

    stack = []
    seen = set()
    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen:
            continue
        seen.add((x, y))
        if not is_white_background(x, y):
            continue
        red, green, blue, _alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    image.save(image_path)


def _register_routes(app: FastAPI) -> None:
    app.include_router(build_public_router(get_db))
    app.include_router(build_workspace_router(get_db))
    app.include_router(build_admin_read_router(get_db, verify_authenticated_admin, verify_admin, LOG_FILE))
    app.include_router(
        build_admin_write_router(
            get_db=get_db,
            verify_admin=verify_admin,
            verify_schedule_editor=verify_schedule_editor,
            verify_schedule_manager=verify_schedule_manager,
            verify_cup_standings_manager=verify_cup_standings_manager,
            verify_suspension_manager=verify_suspension_manager,
            verify_candidate_list_manager=verify_candidate_list_manager,
            set_session_cookie=set_session_cookie,
            clear_session_cookie=clear_session_cookie,
            write_to_log=write_to_log,
        )
    )
    app.include_router(
        build_frontend_router(
            get_db,
            internal_share_token=INTERNAL_SHARE_TOKEN,
            internal_share_header_name=INTERNAL_SHARE_HEADER_NAME,
            internal_render_signing_key=INTERNAL_RENDER_SIGNING_KEY,
            share_cache_root=SHARE_CACHE_ROOT,
            share_template_version=SHARE_TEMPLATE_VERSION,
        )
    )


def configure_http_delivery(app: FastAPI) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

    @app.middleware("http")
    async def add_static_cache_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            if request.query_params.get("v"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "public, max-age=3600"
        return response


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_app_state()
        share_cache_cleanup_task = asyncio.create_task(
            run_share_cache_cleanup_loop(
                SHARE_CACHE_ROOT,
                retention_days=SHARE_CACHE_RETENTION_DAYS,
            )
        )
        try:
            yield
        finally:
            share_cache_cleanup_task.cancel()
            try:
                await share_cache_cleanup_task
            except asyncio.CancelledError:
                pass
            shutdown_app_state()

    app = FastAPI(title="HEIGO联机联赛数据库", lifespan=lifespan)
    configure_http_delivery(app)
    _ensure_static_assets()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.get("/health")(health_check)
    _register_routes(app)
    return app


app = create_app()
