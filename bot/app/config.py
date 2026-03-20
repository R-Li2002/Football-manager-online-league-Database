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
    bot_port: int = 8090
    heigo_base_url: str = "http://127.0.0.1:8080"
    heigo_timeout_seconds: float = 10.0
    onebot_api_root: str = "http://127.0.0.1:3000"
    onebot_access_token: str = ""
    onebot_secret: str = ""
    onebot_self_id: str = ""
    qq_bot_allowed_groups: tuple[str, ...] = ()
    qq_bot_allow_all_groups: bool = False
    bot_reply_mode: str = "echo_response"
    bot_user_cooldown_seconds: int = 5
    bot_group_limit_per_minute: int = 20
    bot_render_base_url: str = "http://heigo:8080"
    internal_share_token: str = ""
    bot_render_timeout_seconds: float = 20.0
    bot_render_cache_ttl_seconds: int = 1800
    bot_output_root: str = "output/qqbot"
    bot_playwright_headless: bool = True

    @classmethod
    def from_env(cls) -> "BotSettings":
        heigo_base_url = os.environ.get("HEIGO_BASE_URL", cls.heigo_base_url).rstrip("/")
        render_base_url = os.environ.get("BOT_RENDER_BASE_URL", heigo_base_url).rstrip("/")
        onebot_api_root = os.environ.get("ONEBOT_API_ROOT", cls.onebot_api_root).rstrip("/")
        return cls(
            bot_port=int(os.environ.get("BOT_PORT", cls.bot_port)),
            heigo_base_url=heigo_base_url,
            heigo_timeout_seconds=float(os.environ.get("HEIGO_TIMEOUT_SECONDS", cls.heigo_timeout_seconds)),
            onebot_api_root=onebot_api_root,
            onebot_access_token=os.environ.get("ONEBOT_ACCESS_TOKEN", "").strip(),
            onebot_secret=os.environ.get("ONEBOT_SECRET", "").strip(),
            onebot_self_id=os.environ.get("ONEBOT_SELF_ID", "").strip(),
            qq_bot_allowed_groups=_parse_csv(os.environ.get("QQ_BOT_ALLOWED_GROUPS")),
            qq_bot_allow_all_groups=_parse_bool(os.environ.get("QQ_BOT_ALLOW_ALL_GROUPS"), default=False),
            bot_reply_mode=os.environ.get("BOT_REPLY_MODE", cls.bot_reply_mode).strip() or cls.bot_reply_mode,
            bot_user_cooldown_seconds=int(
                os.environ.get("BOT_USER_COOLDOWN_SECONDS", cls.bot_user_cooldown_seconds)
            ),
            bot_group_limit_per_minute=int(
                os.environ.get("BOT_GROUP_LIMIT_PER_MINUTE", cls.bot_group_limit_per_minute)
            ),
            bot_render_base_url=render_base_url,
            internal_share_token=os.environ.get("INTERNAL_SHARE_TOKEN", "").strip(),
            bot_render_timeout_seconds=float(
                os.environ.get("BOT_RENDER_TIMEOUT_SECONDS", cls.bot_render_timeout_seconds)
            ),
            bot_render_cache_ttl_seconds=int(
                os.environ.get("BOT_RENDER_CACHE_TTL_SECONDS", cls.bot_render_cache_ttl_seconds)
            ),
            bot_output_root=os.environ.get("BOT_OUTPUT_ROOT", cls.bot_output_root).strip() or cls.bot_output_root,
            bot_playwright_headless=_parse_bool(os.environ.get("BOT_PLAYWRIGHT_HEADLESS"), default=True),
        )

    @property
    def bot_output_path(self) -> Path:
        return Path(self.bot_output_root)
