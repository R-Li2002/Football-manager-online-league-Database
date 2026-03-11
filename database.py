import atexit
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

try:
    from alembic import command
    from alembic.config import Config
except ImportError:  # pragma: no cover - optional fallback for legacy environments
    command = None
    Config = None

from migration_helpers import initialize_runtime_fallback_schema
from operation_audit_store import persist_operation_audit

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./fm_league.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
BASE_DIR = Path(__file__).resolve().parent
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = BASE_DIR / "alembic"
BOOTSTRAP_LOG_PATH = BASE_DIR / "schema_bootstrap.log"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)


def _register_sqlite_adapters() -> None:
    sqlite3.register_adapter(date, lambda value: value.isoformat())
    sqlite3.register_adapter(datetime, lambda value: value.isoformat(sep=" "))


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _configure_engine(active_engine) -> None:
    if active_engine.dialect.name != "sqlite":
        return
    if not event.contains(active_engine, "connect", _set_sqlite_pragma):
        event.listen(active_engine, "connect", _set_sqlite_pragma)


_register_sqlite_adapters()
_configure_engine(engine)
atexit.register(engine.dispose)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _describe_engine(active_engine) -> str:
    url = active_engine.url
    if url.drivername.startswith("sqlite"):
        return f"{url.drivername}:{url.database or ':memory:'}"
    return url.drivername


def record_schema_bootstrap_event(event: str, target_engine=None, detail: str = "") -> None:
    active_engine = target_engine or engine
    BOOTSTRAP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] {event} engine={_describe_engine(active_engine)}"
    if detail:
        message = f"{message} detail={detail}"
    with BOOTSTRAP_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")

    if event.endswith("_failed"):
        status = "failed"
    elif event.endswith("_blocked"):
        status = "blocked"
    elif event.endswith("_started"):
        status = "started"
    else:
        status = "success"

    source = "manual_repair" if event.startswith("manual_") else "startup"
    persist_operation_audit(
        active_engine,
        category="schema_bootstrap",
        action=event,
        status=status,
        summary=message,
        source=source,
        details={"detail": detail, "engine": _describe_engine(active_engine)},
        created_at=datetime.now(),
    )


def run_schema_migrations(target_engine=None) -> bool:
    active_engine = target_engine or engine
    if command is None or Config is None:
        return False
    if not ALEMBIC_INI_PATH.exists() or not ALEMBIC_SCRIPT_LOCATION.exists():
        return False

    alembic_config = Config(str(ALEMBIC_INI_PATH))
    alembic_config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    alembic_config.set_main_option("sqlalchemy.url", str(active_engine.url))

    with active_engine.begin() as conn:
        alembic_config.attributes["connection"] = conn
        command.upgrade(alembic_config, "head")
    return True


def init_database(target_engine=None) -> None:
    active_engine = target_engine or engine
    _configure_engine(active_engine)
    import models  # noqa: F401  # Ensure metadata is populated before migrations/create_all.

    try:
        migrated = run_schema_migrations(active_engine)
    except Exception as exc:
        record_schema_bootstrap_event("alembic_upgrade_failed", active_engine, f"{type(exc).__name__}: {exc}")
        raise

    if migrated:
        record_schema_bootstrap_event("alembic_upgrade_head", active_engine, "startup")
        return

    record_schema_bootstrap_event(
        "runtime_fallback_blocked",
        active_engine,
        "automatic runtime fallback removed; use runtime_schema_repair.py for emergency legacy repair",
    )
    raise RuntimeError(
        "Alembic migrations are unavailable. Automatic runtime schema fallback has been removed. "
        "Use python runtime_schema_repair.py only for emergency legacy repair."
    )


def run_manual_runtime_fallback(target_engine=None) -> None:
    active_engine = target_engine or engine
    _configure_engine(active_engine)
    import models  # noqa: F401  # Ensure metadata is populated before create_all/runtime repair.

    record_schema_bootstrap_event("manual_runtime_fallback_started", active_engine, "operator-invoked repair")
    try:
        initialize_runtime_fallback_schema(active_engine, Base.metadata)
    except Exception as exc:
        record_schema_bootstrap_event("manual_runtime_fallback_failed", active_engine, f"{type(exc).__name__}: {exc}")
        raise
    record_schema_bootstrap_event("manual_runtime_fallback_completed", active_engine, "operator-invoked repair")
