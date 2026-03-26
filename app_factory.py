from __future__ import annotations

from contextlib import asynccontextmanager
import os
import shutil
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app_bootstrap import LOG_FILE, initialize_app_state, shutdown_app_state, write_to_log
from app_security import clear_session_cookie, set_session_cookie
from auth_utils import get_session_username
from database import SessionLocal, engine
from routers.admin_read_routes import build_admin_read_router
from routers.admin_write_routes import build_admin_write_router
from routers.frontend_routes import build_frontend_router
from routers.public_routes import build_public_router

INTERNAL_SHARE_TOKEN = os.environ.get("INTERNAL_SHARE_TOKEN", "").strip()
INTERNAL_SHARE_HEADER_NAME = "X-Internal-Share-Token"
INTERNAL_RENDER_SIGNING_KEY = os.environ.get("INTERNAL_RENDER_SIGNING_KEY", "").strip()
SHARE_CACHE_ROOT = os.environ.get("HEIGO_SHARE_CACHE_ROOT", "data/share-cache").strip() or "data/share-cache"
SHARE_TEMPLATE_VERSION = int(os.environ.get("HEIGO_SHARE_TEMPLATE_VERSION", "2"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    return get_session_username(db, session_token)


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


def _register_routes(app: FastAPI) -> None:
    app.include_router(build_public_router(get_db))
    app.include_router(build_admin_read_router(get_db, verify_admin, LOG_FILE))
    app.include_router(
        build_admin_write_router(
            get_db=get_db,
            verify_admin=verify_admin,
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


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_app_state()
        try:
            yield
        finally:
            shutdown_app_state()

    app = FastAPI(title="HEIGO联机联赛数据库", lifespan=lifespan)
    _ensure_static_assets()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.get("/health")(health_check)
    _register_routes(app)
    return app


app = create_app()
