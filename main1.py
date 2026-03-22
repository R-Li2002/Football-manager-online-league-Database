from contextlib import asynccontextmanager
from datetime import datetime
import os
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth_utils import get_session_username, hash_password
from database import SessionLocal, engine, init_database
from models import Player
from routers.admin_read_routes import build_admin_read_router
from routers.admin_write_routes import build_admin_write_router
from routers.frontend_routes import build_frontend_router
from routers.public_routes import build_public_router
from services import auth_service, league_service
from services.operation_audit_service import import_legacy_admin_log_to_operation_audits

LOG_FILE = "admin_operations.log"
SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 86400
SESSION_COOKIE_SECURE_ENV = "SESSION_COOKIE_SECURE"
SESSION_COOKIE_SECURE_TRUE_VALUES = {"1", "true", "yes", "on"}
SESSION_COOKIE_SECURE_FALSE_VALUES = {"0", "false", "no", "off"}
LOCAL_DEV_HOST = os.environ.get("LOCAL_HOST", "127.0.0.1")
LOCAL_DEV_PORT = int(os.environ.get("LOCAL_PORT", "8001"))
BOOTSTRAP_ADMINS_ENV = "HEIGO_BOOTSTRAP_ADMINS"
INTERNAL_SHARE_TOKEN = os.environ.get("INTERNAL_SHARE_TOKEN", "").strip()
INTERNAL_SHARE_HEADER_NAME = "X-Internal-Share-Token"
INTERNAL_RENDER_SIGNING_KEY = os.environ.get("INTERNAL_RENDER_SIGNING_KEY", "").strip()
SHARE_CACHE_ROOT = os.environ.get("HEIGO_SHARE_CACHE_ROOT", "data/share-cache").strip() or "data/share-cache"
SHARE_TEMPLATE_VERSION = int(os.environ.get("HEIGO_SHARE_TEMPLATE_VERSION", "2"))


def write_to_log(operation: str, details: str, operator: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{operator}] {operation}: {details}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)


def load_bootstrap_admin_accounts_from_env() -> list[tuple[str, str]]:
    raw_accounts = os.environ.get(BOOTSTRAP_ADMINS_ENV, "").strip()
    if not raw_accounts:
        return []

    accounts: list[tuple[str, str]] = []
    for raw_entry in raw_accounts.split(";"):
        entry = raw_entry.strip()
        if not entry:
            continue
        username, separator, password = entry.partition("=")
        username = username.strip()
        password = password.strip()
        if not separator or not username or not password:
            raise RuntimeError(
                f"Invalid {BOOTSTRAP_ADMINS_ENV} entry: {entry!r}. Expected format: username=password;username2=password2"
            )
        accounts.append((username, hash_password(password)))
    return accounts


def initialize_app_state():
    init_database()
    db = SessionLocal()
    try:
        admin_accounts = load_bootstrap_admin_accounts_from_env()
        if admin_accounts:
            auth_service.seed_default_admins(db, admin_accounts)
    finally:
        db.close()
    import_legacy_admin_log_to_operation_audits(engine, LOG_FILE)


def shutdown_app_state():
    engine.dispose()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_app_state()
    try:
        yield
    finally:
        shutdown_app_state()


app = FastAPI(title="HEIGO联机联赛数据库", lifespan=lifespan)

if not os.path.exists("static"):
    os.makedirs("static")

if os.path.exists("heigo.jpeg") and not os.path.exists("static/heigo.jpeg"):
    import shutil

    shutil.copy2("heigo.jpeg", "static/heigo.jpeg")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    return get_session_username(db, session_token)


def get_session_cookie_secure_mode() -> str:
    raw_mode = os.environ.get(SESSION_COOKIE_SECURE_ENV, "auto").strip().lower()
    return raw_mode or "auto"


def request_uses_https(request: Request | None) -> bool:
    if request is None:
        return False

    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto:
        protocol = forwarded_proto.split(",", 1)[0].strip().lower()
        if protocol:
            return protocol == "https"

    return request.url.scheme == "https"


def should_use_secure_session_cookie(request: Request | None = None) -> bool:
    secure_mode = get_session_cookie_secure_mode()
    if secure_mode in SESSION_COOKIE_SECURE_TRUE_VALUES:
        return True
    if secure_mode in SESSION_COOKIE_SECURE_FALSE_VALUES:
        return False
    return request_uses_https(request)


def set_session_cookie(response: Response, token: str, request: Request | None = None):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=should_use_secure_session_cookie(request),
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response, request: Request | None = None):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=should_use_secure_session_cookie(request),
        httponly=True,
        samesite="lax",
    )


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


def calculate_player_wage_payload(initial_ca: int, current_ca: int, pa: int, age: int, position: str, db: Session):
    return league_service.calculate_player_wage_payload(
        initial_ca=initial_ca,
        current_ca=current_ca,
        pa=pa,
        age=age,
        position=position,
        db=db,
    )


def refresh_player_financials(player: Player, db: Session):
    return league_service.refresh_player_financials(player, db)


def recalculate_team_stats(db: Session, commit: bool = True, affected_team_ids=None, stat_scopes=None, refresh_mode=None):
    league_service.recalculate_team_stats(
        db,
        commit=commit,
        affected_team_ids=affected_team_ids,
        stat_scopes=stat_scopes,
        refresh_mode=refresh_mode,
    )


def calculate_team_final_wage(team, players):
    return league_service.calculate_team_final_wage(team, players)


def run_local_server():
    import uvicorn

    os.environ.setdefault("ALLOW_MANUAL_RUNTIME_FALLBACK", "1")
    uvicorn.run("main1:app", host=LOCAL_DEV_HOST, port=LOCAL_DEV_PORT, reload=False)


if __name__ == "__main__":
    run_local_server()
