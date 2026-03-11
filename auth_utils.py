import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import AdminSession, AdminUser

PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
SESSION_TTL = timedelta(days=1)


def hash_legacy_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str, *, salt: Optional[str] = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"{PBKDF2_PREFIX}${iterations}${salt}${digest}"


def is_modern_password_hash(password_hash: str) -> bool:
    return password_hash.startswith(f"{PBKDF2_PREFIX}$")


def verify_password(password: str, password_hash: str) -> bool:
    if is_modern_password_hash(password_hash):
        try:
            _, iterations, salt, digest = password_hash.split("$", 3)
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, digest)

    return hmac.compare_digest(hash_legacy_password(password), password_hash)


def verify_password_and_upgrade(db: Session, admin: AdminUser, password: str) -> bool:
    if not verify_password(password, admin.password_hash):
        return False

    if not is_modern_password_hash(admin.password_hash):
        admin.password_hash = hash_password(password)
        db.add(admin)
        db.flush()

    return True


def create_session(db: Session, username: str, *, ttl: timedelta = SESSION_TTL) -> str:
    token = secrets.token_hex(32)
    now = datetime.now(UTC)
    db.add(
        AdminSession(
            token=token,
            username=username,
            created_at=now,
            expires_at=now + ttl,
        )
    )
    db.flush()
    return token


def delete_session(db: Session, token: Optional[str]) -> None:
    if not token:
        return
    db.query(AdminSession).filter(AdminSession.token == token).delete()
    db.flush()


def cleanup_expired_sessions(db: Session) -> None:
    db.query(AdminSession).filter(AdminSession.expires_at <= datetime.now(UTC)).delete()
    db.flush()


def get_session_username(db: Session, token: Optional[str]) -> Optional[str]:
    if not token:
        return None

    cleanup_expired_sessions(db)
    session = db.query(AdminSession).filter(AdminSession.token == token).first()
    if not session:
        return None
    return session.username
