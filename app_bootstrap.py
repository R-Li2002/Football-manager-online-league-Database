from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from auth_utils import hash_password
from database import SessionLocal, engine, init_database
from services import auth_service
from services.operation_audit_service import import_legacy_admin_log_to_operation_audits

LOG_FILE = str(Path(__file__).resolve().parent / "output" / "logs" / "admin_operations.log")
BOOTSTRAP_ADMINS_ENV = "HEIGO_BOOTSTRAP_ADMINS"
BOOTSTRAP_SCHEDULE_ADMINS_ENV = "HEIGO_SCHEDULE_ADMINS"


def write_to_log(operation: str, details: str, operator: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{operator}] {operation}: {details}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)


def _load_bootstrap_accounts_from_env(env_name: str, role: str) -> list[tuple[str, str, str]]:
    raw_accounts = os.environ.get(env_name, "").strip()
    if not raw_accounts:
        return []

    accounts: list[tuple[str, str, str]] = []
    for raw_entry in raw_accounts.split(";"):
        entry = raw_entry.strip()
        if not entry:
            continue
        username, separator, password = entry.partition("=")
        username = username.strip()
        password = password.strip()
        if not separator or not username or not password:
            raise RuntimeError(
                f"Invalid {env_name} entry: {entry!r}. Expected format: username=password;username2=password2"
            )
        accounts.append((username, hash_password(password), role))
    return accounts


def load_bootstrap_admin_accounts_from_env() -> list[tuple[str, str, str]]:
    return _load_bootstrap_accounts_from_env(BOOTSTRAP_ADMINS_ENV, "admin")


def load_bootstrap_schedule_accounts_from_env() -> list[tuple[str, str, str]]:
    return _load_bootstrap_accounts_from_env(BOOTSTRAP_SCHEDULE_ADMINS_ENV, "schedule_editor")


def initialize_app_state() -> None:
    init_database()
    db = SessionLocal()
    try:
        admin_accounts = load_bootstrap_admin_accounts_from_env() + load_bootstrap_schedule_accounts_from_env()
        if admin_accounts:
            auth_service.seed_default_admins(db, admin_accounts)
    finally:
        db.close()
    import_legacy_admin_log_to_operation_audits(engine, LOG_FILE)


def shutdown_app_state() -> None:
    engine.dispose()
