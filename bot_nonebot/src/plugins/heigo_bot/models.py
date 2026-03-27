from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CommandType = Literal["help", "player_image", "wage_text", "wage_image", "roster_text", "roster_image", "unknown"]
ReplyType = Literal["text", "image", "noop"]


@dataclass(frozen=True)
class CommandSpec:
    command_type: CommandType
    raw_text: str
    normalized_text: str
    keyword: str = ""
    uid: int | None = None
    team_name: str | None = None
    step: int = 0
    page: int = 1
    version: str | None = None


@dataclass(frozen=True)
class ReplySpec:
    reply_type: ReplyType
    text: str = ""
    image_url: str = ""
