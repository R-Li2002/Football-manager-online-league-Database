from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from auth_utils import cleanup_expired_sessions, create_session, delete_session, get_session_username, verify_password_and_upgrade
from models import AdminUser
from repositories.admin_user_repository import get_admin_by_username
from schemas_read import AuthStatusResponse
from schemas_write import LoginResponse, LogoutResponse
from services.operation_audit_service import AUDIT_SOURCE_ADMIN_UI, persist_admin_operation_audit


def _persist_auth_audit(
    db: Session,
    *,
    action: str,
    status: str,
    operator: str | None,
    summary: str,
    request_payload: dict | None = None,
    response_payload: dict | None = None,
    details_text: str | None = None,
) -> None:
    bind = db.get_bind()
    if bind is None:
        return
    persist_admin_operation_audit(
        bind,
        category="auth",
        action=action,
        operator=operator,
        status=status,
        summary=summary,
        source=AUDIT_SOURCE_ADMIN_UI,
        operation_label="登录" if action == "login" else "登出",
        details_text=details_text or summary,
        request_payload=request_payload,
        response_payload=response_payload,
    )


FULL_ADMIN_ROLE = "admin"
SCHEDULE_EDITOR_ROLE = "schedule_editor"
ROLE_LABELS = {
    FULL_ADMIN_ROLE: "完整管理员",
    SCHEDULE_EDITOR_ROLE: "赛程维护",
}


def normalize_admin_role(role: str | None) -> str:
    normalized = str(role or "").strip().lower()
    return normalized if normalized in ROLE_LABELS else FULL_ADMIN_ROLE


def can_manage_admin(role: str | None) -> bool:
    return normalize_admin_role(role) == FULL_ADMIN_ROLE


def can_manage_schedule(role: str | None) -> bool:
    return normalize_admin_role(role) in {FULL_ADMIN_ROLE, SCHEDULE_EDITOR_ROLE}


def seed_default_admins(db: Session, admin_accounts: list[tuple[str, str] | tuple[str, str, str]]) -> None:
    cleanup_expired_sessions(db)
    created = False

    for account in admin_accounts:
        username, password = account[0], account[1]
        role = normalize_admin_role(account[2] if len(account) >= 3 else FULL_ADMIN_ROLE)
        existing_admin = get_admin_by_username(db, username)
        if existing_admin:
            if not getattr(existing_admin, "role", None):
                existing_admin.role = role
                created = True
            continue
        db.add(AdminUser(username=username, password_hash=password, role=role))
        created = True

    if created:
        db.commit()
    else:
        db.rollback()


def login_admin(
    db: Session,
    username: str,
    password: str,
    request: Request,
    response: Response,
    *,
    set_session_cookie,
    write_to_log,
) -> LoginResponse:
    admin = get_admin_by_username(db, username)
    if not admin or not verify_password_and_upgrade(db, admin, password):
        db.rollback()
        _persist_auth_audit(
            db,
            action="login",
            status="failed",
            operator=username,
            summary=f"管理员登录失败: {username}",
            request_payload={"username": username},
            details_text="管理员登录失败",
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    cleanup_expired_sessions(db)
    session_token = create_session(db, admin.username)
    db.commit()
    set_session_cookie(response, session_token, request=request)
    write_to_log("登录", "管理员登录成功", admin.username)
    role = normalize_admin_role(admin.role)
    payload = LoginResponse(
        success=True,
        username=admin.username,
        role=role,
        can_manage_admin=can_manage_admin(role),
        can_manage_schedule=can_manage_schedule(role),
    )
    _persist_auth_audit(
        db,
        action="login",
        status="success",
        operator=admin.username,
        summary="管理员登录成功",
        request_payload={"username": username},
        response_payload=payload.model_dump(mode="json"),
        details_text="管理员登录成功",
    )
    return payload


def logout_admin(
    db: Session,
    request: Request,
    response: Response,
    session_token: str | None,
    *,
    clear_session_cookie,
    write_to_log,
) -> LogoutResponse:
    username = get_session_username(db, session_token) or "unknown"
    delete_session(db, session_token)
    db.commit()
    clear_session_cookie(response, request=request)
    write_to_log("登出", "管理员登出", username)
    payload = LogoutResponse(success=True)
    _persist_auth_audit(
        db,
        action="logout",
        status="success",
        operator=username,
        summary="管理员登出",
        response_payload=payload.model_dump(mode="json"),
        details_text="管理员登出",
    )
    return payload


def get_auth_status(db: Session, username: str | None) -> AuthStatusResponse:
    if not username:
        return AuthStatusResponse(authenticated=False)
    admin = get_admin_by_username(db, username)
    if not admin:
        return AuthStatusResponse(authenticated=False)
    role = normalize_admin_role(admin.role)
    return AuthStatusResponse(
        authenticated=True,
        username=username,
        role=role,
        can_manage_admin=can_manage_admin(role),
        can_manage_schedule=can_manage_schedule(role),
    )


def get_admin_role(db: Session, username: str | None) -> str | None:
    if not username:
        return None
    admin = get_admin_by_username(db, username)
    return normalize_admin_role(admin.role) if admin else None
