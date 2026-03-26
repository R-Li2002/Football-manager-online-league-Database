from __future__ import annotations

import os

from fastapi import Request, Response

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 86400
SESSION_COOKIE_SECURE_ENV = "SESSION_COOKIE_SECURE"
SESSION_COOKIE_SECURE_TRUE_VALUES = {"1", "true", "yes", "on"}
SESSION_COOKIE_SECURE_FALSE_VALUES = {"0", "false", "no", "off"}


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


def set_session_cookie(response: Response, token: str, request: Request | None = None) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=should_use_secure_session_cookie(request),
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response, request: Request | None = None) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=should_use_secure_session_cookie(request),
        httponly=True,
        samesite="lax",
    )
