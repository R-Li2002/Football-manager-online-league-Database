from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field


MessageType = Literal["group", "private"]
CQ_AT_PATTERN = re.compile(r"\[CQ:at,qq=(\d+)\]")


class OneBotMessageEvent(BaseModel):
    post_type: str
    message_type: MessageType
    message_id: str | None = None
    self_id: str | None = None
    user_id: str | None = None
    group_id: str | None = None
    content: str = ""
    mentions_robot: bool = False
    raw_payload: dict[str, Any] = Field(default_factory=dict)


def _extract_message_text(payload: dict[str, Any]) -> str:
    raw_message = payload.get("raw_message")
    if isinstance(raw_message, str) and raw_message.strip():
        return raw_message

    message = payload.get("message")
    if isinstance(message, str):
        return message
    if not isinstance(message, list):
        return ""

    parts: list[str] = []
    for segment in message:
        if not isinstance(segment, dict):
            continue
        segment_type = str(segment.get("type") or "").strip()
        data = segment.get("data") or {}
        if segment_type == "text":
            parts.append(str(data.get("text") or ""))
        elif segment_type == "at":
            target = str(data.get("qq") or "").strip()
            if target:
                parts.append(f"[CQ:at,qq={target}]")
    return "".join(parts)


def _detect_mentions_robot(payload: dict[str, Any], self_id: str) -> bool:
    if payload.get("to_me") is True:
        return True
    if not self_id:
        return False

    message = payload.get("message")
    if isinstance(message, list):
        for segment in message:
            if not isinstance(segment, dict):
                continue
            if str(segment.get("type") or "").strip() != "at":
                continue
            target = str((segment.get("data") or {}).get("qq") or "").strip()
            if target == self_id:
                return True

    content = _extract_message_text(payload)
    return any(match == self_id for match in CQ_AT_PATTERN.findall(content))


def normalize_onebot_message_event(payload: dict[str, Any], configured_self_id: str = "") -> OneBotMessageEvent | None:
    post_type = str(payload.get("post_type") or "").strip()
    message_type = str(payload.get("message_type") or "").strip()
    if post_type != "message" or message_type not in {"group", "private"}:
        return None

    self_id = configured_self_id or str(payload.get("self_id") or "").strip()
    content = _extract_message_text(payload)
    return OneBotMessageEvent(
        post_type=post_type,
        message_type=message_type,
        message_id=str(payload.get("message_id") or "").strip() or None,
        self_id=self_id or None,
        user_id=str(payload.get("user_id") or "").strip() or None,
        group_id=str(payload.get("group_id") or "").strip() or None,
        content=content,
        mentions_robot=(message_type == "private") or _detect_mentions_robot(payload, self_id),
        raw_payload=payload,
    )
