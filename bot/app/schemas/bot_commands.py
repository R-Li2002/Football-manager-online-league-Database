from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CommandType = Literal["help", "player", "player_image", "roster", "wage", "unknown"]
ReplyType = Literal["text", "image", "noop"]


class BotCommand(BaseModel):
    command_type: CommandType
    raw_text: str
    normalized_text: str
    keyword: str = ""
    uid: int | None = None
    team_name: str | None = None
    page: int = 1
    version: str | None = None
    step: int = 0


class PreparedReply(BaseModel):
    reply_type: ReplyType
    text: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
