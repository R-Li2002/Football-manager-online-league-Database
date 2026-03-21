from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.config import BotSettings
from app.schemas.bot_commands import PreparedReply
from app.utils.logging import get_logger


logger = get_logger(__name__)


class OneBotClient:
    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.reply_mode = settings.bot_reply_mode
        self._client = httpx.AsyncClient(base_url=settings.onebot_api_root, timeout=20.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _authorized_headers(self) -> dict[str, str]:
        token = self.settings.onebot_access_token
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    async def _post_action(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._client.post(
            f"/{action}",
            headers=self._authorized_headers(),
            json=params or {},
        )
        response.raise_for_status()
        payload = response.json()
        retcode = payload.get("retcode", -1)
        if str(payload.get("status") or "").lower() != "ok" or int(retcode) != 0:
            raise RuntimeError(f"OneBot action failed: {action}")
        return payload

    async def get_status(self) -> dict[str, Any]:
        try:
            payload = await self._post_action("get_status")
            data = payload.get("data") or {}
            return {
                "status": "ok",
                "online": data.get("online", True),
                "good": data.get("good", True),
            }
        except Exception:
            payload = await self._post_action("get_login_info")
            data = payload.get("data") or {}
            return {
                "status": "ok",
                "user_id": data.get("user_id"),
                "nickname": data.get("nickname"),
            }

    def _build_text_message(self, text: str, reply_to: str | None = None) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
        if reply_to:
            segments.append({"type": "reply", "data": {"id": reply_to}})
        segments.append({"type": "text", "data": {"text": text or " "}})
        return segments

    def _build_image_message(self, reply: PreparedReply, reply_to: str | None = None) -> list[dict[str, Any]]:
        image_path = Path(str(reply.meta.get("image_path") or ""))
        if not image_path.exists():
            raise FileNotFoundError(f"Rendered image not found: {image_path}")

        segments: list[dict[str, Any]] = []
        if reply_to:
            segments.append({"type": "reply", "data": {"id": reply_to}})
        if reply.text:
            segments.append({"type": "text", "data": {"text": reply.text}})
        segments.append({"type": "image", "data": {"file": str(image_path)}})
        return segments

    async def _send_group_message(
        self,
        *,
        group_id: str,
        message: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self._post_action("send_group_msg", {"group_id": int(group_id), "message": message})

    async def _send_private_message(
        self,
        *,
        user_id: str,
        message: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self._post_action("send_private_msg", {"user_id": int(user_id), "message": message})

    async def dispatch_reply(
        self,
        *,
        message_type: str,
        group_id: str | None,
        user_id: str | None,
        message_id: str | None,
        reply: PreparedReply,
    ) -> dict[str, Any]:
        if self.reply_mode == "off":
            return {"mode": "off", "delivered": False}

        if self.reply_mode != "onebot":
            return {
                "mode": self.reply_mode,
                "delivered": False,
                "message_type": message_type,
                "group_id": group_id,
                "user_id": user_id,
                "reply": reply.model_dump(),
            }

        target_label = group_id if message_type == "group" else user_id
        if message_type == "group" and not group_id:
            return {"mode": self.reply_mode, "delivered": False, "reason": "missing_group_id"}
        if message_type == "private" and not user_id:
            return {"mode": self.reply_mode, "delivered": False, "reason": "missing_user_id"}

        try:
            message = (
                self._build_image_message(reply, message_id)
                if reply.reply_type == "image"
                else self._build_text_message(reply.text, message_id)
            )
            payload = (
                await self._send_group_message(group_id=group_id, message=message)
                if message_type == "group"
                else await self._send_private_message(user_id=user_id, message=message)
            )
        except Exception as exc:
            if reply.reply_type == "image":
                fallback_text = str(
                    reply.meta.get("fallback_text")
                    or f"球员图发送失败，已降级为文本：\n{reply.text}"
                )
                try:
                    payload = (
                        await self._send_group_message(
                            group_id=group_id,
                            message=self._build_text_message(fallback_text, message_id),
                        )
                        if message_type == "group"
                        else await self._send_private_message(
                            user_id=user_id,
                            message=self._build_text_message(fallback_text, message_id),
                        )
                    )
                    return {
                        "mode": self.reply_mode,
                        "delivered": True,
                        "target": target_label,
                        "reply_type": "text",
                        "degraded_from": "image",
                        "error": str(exc),
                        "payload": payload,
                    }
                except Exception as fallback_exc:
                    logger.exception(
                        "Failed to degrade image reply to text target=%s mode=%s",
                        target_label,
                        self.reply_mode,
                    )
                    return {
                        "mode": self.reply_mode,
                        "delivered": False,
                        "target": target_label,
                        "reply_type": "image",
                        "degraded_from": "image",
                        "error": str(exc),
                        "fallback_error": str(fallback_exc),
                    }

            logger.exception(
                "Failed to deliver OneBot reply type=%s target=%s mode=%s",
                reply.reply_type,
                target_label,
                self.reply_mode,
            )
            return {
                "mode": self.reply_mode,
                "delivered": False,
                "target": target_label,
                "reply_type": reply.reply_type,
                "error": str(exc),
            }

        logger.info("Delivered OneBot reply type=%s mode=%s target=%s", reply.reply_type, self.reply_mode, target_label)
        return {
            "mode": self.reply_mode,
            "delivered": True,
            "target": target_label,
            "reply_type": reply.reply_type,
            "payload": payload,
        }
