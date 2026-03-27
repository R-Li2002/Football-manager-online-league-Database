from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class BotSettings:
    heigo_base_url: str
    heigo_render_base_url: str
    internal_render_signing_key: str
    heigo_render_ttl_seconds: int
    bot_default_theme: str
    bot_roster_page_size: int
    qq_bot_allowed_groups: tuple[str, ...]
    qq_bot_allow_all_groups: bool
    bot_user_cooldown_seconds: int
    bot_group_limit_per_minute: int

    @classmethod
    def from_env(cls) -> "BotSettings":
        heigo_base_url = os.environ.get("HEIGO_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        render_base_url = os.environ.get("HEIGO_RENDER_BASE_URL", heigo_base_url).rstrip("/")
        return cls(
            heigo_base_url=heigo_base_url,
            heigo_render_base_url=render_base_url,
            internal_render_signing_key=os.environ.get("INTERNAL_RENDER_SIGNING_KEY", "").strip(),
            heigo_render_ttl_seconds=int(os.environ.get("HEIGO_RENDER_TTL_SECONDS", "90")),
            bot_default_theme=os.environ.get("BOT_DEFAULT_THEME", "dark").strip() or "dark",
            bot_roster_page_size=max(20, min(20, int(os.environ.get("BOT_ROSTER_PAGE_SIZE", "20")))),
            qq_bot_allowed_groups=_parse_csv(os.environ.get("QQ_BOT_ALLOWED_GROUPS")),
            qq_bot_allow_all_groups=_parse_bool(os.environ.get("QQ_BOT_ALLOW_ALL_GROUPS"), default=False),
            bot_user_cooldown_seconds=int(os.environ.get("BOT_USER_COOLDOWN_SECONDS", "5")),
            bot_group_limit_per_minute=int(os.environ.get("BOT_GROUP_LIMIT_PER_MINUTE", "20")),
        )

    def is_group_allowed(self, group_id: str | None) -> bool:
        if self.qq_bot_allow_all_groups:
            return True
        if not group_id:
            return False
        return group_id in self.qq_bot_allowed_groups
