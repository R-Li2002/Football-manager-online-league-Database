from typing import Callable

from fastapi import HTTPException


LogWriter = Callable[[str, str, str], None]


def require_admin(admin: str | None) -> str:
    if not admin:
        raise HTTPException(status_code=401, detail="未授权")
    return admin
