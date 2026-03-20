from __future__ import annotations

import hashlib
import hmac

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.clients.heigo_client import HeigoClient
from app.clients.onebot_client import OneBotClient
from app.config import BotSettings
from app.schemas.bot_commands import PreparedReply
from app.schemas.onebot_events import normalize_onebot_message_event
from app.services.command_service import parse_command
from app.services.rate_limit_service import InMemoryRateLimitService
from app.services.render_service import PlayerShareRenderService
from app.services.reply_service import build_reply
from app.services.whitelist_service import is_group_allowed
from app.utils.logging import get_logger


logger = get_logger(__name__)


def _verify_onebot_signature(secret: str, signature: str | None, body: bytes) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha1=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def _build_handler_error_reply(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, httpx.TimeoutException):
        return "heigo_timeout", "HEIGO 服务请求超时，请稍后再试。"
    if isinstance(exc, httpx.HTTPStatusError):
        return "heigo_http_error", "HEIGO 服务暂时不可用，请稍后再试。"
    if isinstance(exc, httpx.HTTPError):
        return "heigo_request_error", "机器人访问 HEIGO 服务失败，请稍后再试。"
    if isinstance(exc, FileNotFoundError):
        return "rendered_file_missing", "球员图缓存文件不存在，请稍后重试。"
    return "handler_error", "机器人处理请求时出现异常，请稍后再试。"


def build_onebot_router(
    settings: BotSettings,
    heigo_client: HeigoClient,
    onebot_client: OneBotClient,
    rate_limit_service: InMemoryRateLimitService,
    render_service: PlayerShareRenderService,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        detail = {
            "status": "ok",
            "reply_mode": settings.bot_reply_mode,
            "heigo_api": "ok",
            "onebot_api": "disabled",
            "config": {
                "onebot_access_token_configured": bool(settings.onebot_access_token),
                "onebot_secret_configured": bool(settings.onebot_secret),
                "onebot_self_id_configured": bool(settings.onebot_self_id),
                "internal_share_token_configured": bool(settings.internal_share_token),
                "allow_all_groups": settings.qq_bot_allow_all_groups,
                "allowed_group_count": len(settings.qq_bot_allowed_groups),
                "playwright_headless": settings.bot_playwright_headless,
            },
        }
        try:
            heigo_health = await heigo_client.get_health()
            detail["heigo_api"] = heigo_health.get("status", "ok")
            if detail["heigo_api"] != "ok":
                detail["status"] = "error"
        except Exception as exc:
            detail["status"] = "error"
            detail["heigo_api"] = "error"
            detail["heigo_error"] = type(exc).__name__

        if settings.bot_reply_mode == "onebot":
            try:
                onebot_status = await onebot_client.get_status()
                if onebot_status.get("online") is False or onebot_status.get("good") is False:
                    detail["status"] = "error"
                    detail["onebot_api"] = "offline"
                    detail["onebot_status"] = onebot_status
                else:
                    detail["onebot_api"] = "ok"
                    detail["onebot_status"] = onebot_status
            except Exception as exc:
                detail["status"] = "error"
                detail["onebot_api"] = "error"
                detail["onebot_error"] = type(exc).__name__

        if detail["status"] != "ok":
            raise HTTPException(status_code=503, detail=detail)
        return detail

    @router.post("/onebot/events")
    async def receive_onebot_event(request: Request):
        raw_body = await request.body()
        if not _verify_onebot_signature(
            settings.onebot_secret,
            request.headers.get("X-Signature"),
            raw_body,
        ):
            return {"ack": False, "ignored": True, "reason": "invalid_signature"}

        payload = await request.json() if raw_body else {}
        if not isinstance(payload, dict):
            return {"ack": False, "ignored": True, "reason": "invalid_payload"}

        event = normalize_onebot_message_event(payload, configured_self_id=settings.onebot_self_id)
        if not event:
            return {"ack": True, "ignored": True, "reason": "unsupported_event"}

        if event.message_type == "group" and not event.mentions_robot:
            return {"ack": True, "ignored": True, "reason": "robot_not_mentioned"}

        if event.message_type == "group" and not is_group_allowed(settings, event.group_id, event.group_id):
            return {"ack": True, "ignored": True, "reason": "group_not_allowed"}

        if event.user_id:
            allowed, retry_after = rate_limit_service.check_user_cooldown(
                f"user:{event.user_id}",
                settings.bot_user_cooldown_seconds,
            )
            if not allowed:
                return {"ack": True, "ignored": True, "reason": "user_cooldown", "retry_after": retry_after}

        if event.message_type == "group":
            group_key = event.group_id or "unknown"
            allowed, retry_after = rate_limit_service.check_group_window(
                f"group:{group_key}",
                settings.bot_group_limit_per_minute,
            )
            if not allowed:
                return {"ack": True, "ignored": True, "reason": "group_rate_limited", "retry_after": retry_after}

        command = None
        try:
            command = parse_command(event.content)
            reply = await build_reply(command, heigo_client, settings, render_service)
            dispatch_result = await onebot_client.dispatch_reply(
                message_type=event.message_type,
                group_id=event.group_id,
                user_id=event.user_id,
                message_id=event.message_id,
                reply=reply,
            )
        except Exception as exc:
            error_reason, error_text = _build_handler_error_reply(exc)
            logger.exception(
                "Failed to handle OneBot event type=%s target=%s",
                event.message_type,
                event.group_id or event.user_id,
            )
            reply = PreparedReply(
                reply_type="text",
                text=error_text,
                meta={"error": type(exc).__name__},
            )
            dispatch_result = await onebot_client.dispatch_reply(
                message_type=event.message_type,
                group_id=event.group_id,
                user_id=event.user_id,
                message_id=event.message_id,
                reply=reply,
            )
            return {
                "ack": True,
                "handled": False,
                "reason": error_reason,
                "error": type(exc).__name__,
                "event": event.model_dump(),
                "command": command.model_dump() if command else None,
                "reply": reply.model_dump(),
                "dispatch": dispatch_result,
            }

        logger.info(
            "Handled OneBot event type=%s command=%s target=%s",
            event.message_type,
            command.command_type,
            event.group_id or event.user_id,
        )
        return {
            "ack": True,
            "handled": True,
            "event": event.model_dump(),
            "command": command.model_dump(),
            "reply": reply.model_dump(),
            "dispatch": dispatch_result,
        }

    return router
