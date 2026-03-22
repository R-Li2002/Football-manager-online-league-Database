from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass


def normalize_theme(theme: str | None) -> str:
    return "light" if theme == "light" else "dark"


def normalize_step(step: int | None) -> int:
    return max(0, min(5, int(step or 0)))


def normalize_page(page: int | None) -> int:
    return max(1, min(20, int(page or 1)))


def _sign_payload(signing_key: str, payload: str) -> str:
    digest = hmac.new(
        signing_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_render_signature_payload(
    *,
    uid: int,
    version: str | None,
    step: int,
    theme: str,
    exp: int,
) -> str:
    return (
        f"type=player"
        f"&uid={int(uid)}"
        f"&version={(version or '').strip()}"
        f"&step={normalize_step(step)}"
        f"&theme={normalize_theme(theme)}"
        f"&exp={int(exp)}"
    )


def build_wage_render_signature_payload(*, uid: int, theme: str, exp: int) -> str:
    return (
        f"type=wage"
        f"&uid={int(uid)}"
        f"&theme={normalize_theme(theme)}"
        f"&exp={int(exp)}"
    )


def build_roster_render_signature_payload(*, team_name: str, page: int, theme: str, exp: int) -> str:
    return (
        f"type=roster"
        f"&team={(team_name or '').strip()}"
        f"&page={normalize_page(page)}"
        f"&theme={normalize_theme(theme)}"
        f"&exp={int(exp)}"
    )


def sign_player_render_request(
    signing_key: str,
    *,
    uid: int,
    version: str | None,
    step: int,
    theme: str,
    exp: int,
) -> str:
    return _sign_payload(
        signing_key,
        build_render_signature_payload(
            uid=uid,
            version=version,
            step=step,
            theme=theme,
            exp=exp,
        ),
    )


def sign_wage_render_request(signing_key: str, *, uid: int, theme: str, exp: int) -> str:
    return _sign_payload(signing_key, build_wage_render_signature_payload(uid=uid, theme=theme, exp=exp))


def sign_roster_render_request(signing_key: str, *, team_name: str, page: int, theme: str, exp: int) -> str:
    return _sign_payload(
        signing_key,
        build_roster_render_signature_payload(team_name=team_name, page=page, theme=theme, exp=exp),
    )


@dataclass(frozen=True)
class RenderSignatureValidationResult:
    ok: bool
    detail: str = "ok"


def _validate_signature(
    signing_key: str,
    *,
    payload: str,
    provided_signature: str | None,
    exp: int,
    now_ts: int | None,
) -> RenderSignatureValidationResult:
    if not signing_key:
        return RenderSignatureValidationResult(ok=False, detail="internal_render_not_configured")

    current_ts = int(now_ts if now_ts is not None else time.time())
    if int(exp) < current_ts:
        return RenderSignatureValidationResult(ok=False, detail="render_url_expired")

    expected_signature = _sign_payload(signing_key, payload)
    if not hmac.compare_digest(expected_signature, (provided_signature or "").strip()):
        return RenderSignatureValidationResult(ok=False, detail="invalid_signature")

    return RenderSignatureValidationResult(ok=True)


def validate_player_render_signature(
    signing_key: str,
    *,
    uid: int,
    version: str | None,
    step: int,
    theme: str,
    exp: int,
    provided_signature: str | None,
    now_ts: int | None = None,
) -> RenderSignatureValidationResult:
    return _validate_signature(
        signing_key,
        payload=build_render_signature_payload(
            uid=uid,
            version=version,
            step=step,
            theme=theme,
            exp=exp,
        ),
        provided_signature=provided_signature,
        exp=exp,
        now_ts=now_ts,
    )


def validate_wage_render_signature(
    signing_key: str,
    *,
    uid: int,
    theme: str,
    exp: int,
    provided_signature: str | None,
    now_ts: int | None = None,
) -> RenderSignatureValidationResult:
    return _validate_signature(
        signing_key,
        payload=build_wage_render_signature_payload(uid=uid, theme=theme, exp=exp),
        provided_signature=provided_signature,
        exp=exp,
        now_ts=now_ts,
    )


def validate_roster_render_signature(
    signing_key: str,
    *,
    team_name: str,
    page: int,
    theme: str,
    exp: int,
    provided_signature: str | None,
    now_ts: int | None = None,
) -> RenderSignatureValidationResult:
    return _validate_signature(
        signing_key,
        payload=build_roster_render_signature_payload(team_name=team_name, page=page, theme=theme, exp=exp),
        provided_signature=provided_signature,
        exp=exp,
        now_ts=now_ts,
    )
