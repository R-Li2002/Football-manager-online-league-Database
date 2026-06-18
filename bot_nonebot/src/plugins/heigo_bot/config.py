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


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _parse_hours(value: str | None, default: tuple[int, ...]) -> tuple[int, ...]:
    raw_items = _parse_csv(value)
    if not raw_items:
        return default
    hours: list[int] = []
    for item in raw_items:
        try:
            hour = int(item)
        except ValueError:
            continue
        if 0 <= hour <= 23 and hour not in hours:
            hours.append(hour)
    return tuple(hours) or default


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
    news_rsshub_base_url: str = "https://rsshub.app"
    news_cache_ttl_seconds: int = 600
    news_item_limit: int = 5
    news_broadcast_groups: tuple[str, ...] = ()
    news_daily_hour: int = 9
    news_headline_hours: tuple[int, ...] = (12, 15, 18)
    news_seen_store_path: str = "/app/data/bot-news-state.json"

    @classmethod
    def from_env(cls) -> "BotSettings":
        heigo_base_url = os.environ.get("HEIGO_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        render_base_url = os.environ.get("HEIGO_RENDER_BASE_URL", heigo_base_url).rstrip("/")
        allowed_groups = _parse_csv(os.environ.get("QQ_BOT_ALLOWED_GROUPS"))
        broadcast_groups = _parse_csv(os.environ.get("NEWS_BROADCAST_GROUPS")) or allowed_groups
        return cls(
            heigo_base_url=heigo_base_url,
            heigo_render_base_url=render_base_url,
            internal_render_signing_key=os.environ.get("INTERNAL_RENDER_SIGNING_KEY", "").strip(),
            heigo_render_ttl_seconds=_parse_int(os.environ.get("HEIGO_RENDER_TTL_SECONDS"), 90),
            bot_default_theme=os.environ.get("BOT_DEFAULT_THEME", "dark").strip() or "dark",
            bot_roster_page_size=max(1, min(30, _parse_int(os.environ.get("BOT_ROSTER_PAGE_SIZE"), 20))),
            qq_bot_allowed_groups=allowed_groups,
            qq_bot_allow_all_groups=_parse_bool(os.environ.get("QQ_BOT_ALLOW_ALL_GROUPS"), default=False),
            bot_user_cooldown_seconds=_parse_int(os.environ.get("BOT_USER_COOLDOWN_SECONDS"), 5),
            bot_group_limit_per_minute=_parse_int(os.environ.get("BOT_GROUP_LIMIT_PER_MINUTE"), 20),
            news_rsshub_base_url=os.environ.get("NEWS_RSSHUB_BASE_URL", "https://rsshub.app").rstrip("/"),
            news_cache_ttl_seconds=max(60, _parse_int(os.environ.get("NEWS_CACHE_TTL_SECONDS"), 600)),
            news_item_limit=max(1, min(10, _parse_int(os.environ.get("NEWS_ITEM_LIMIT"), 5))),
            news_broadcast_groups=broadcast_groups,
            news_daily_hour=max(0, min(23, _parse_int(os.environ.get("NEWS_DAILY_HOUR") or os.environ.get("NEWS_MORNING_HOUR"), 9))),
            news_headline_hours=_parse_hours(os.environ.get("NEWS_HEADLINE_HOURS"), (12, 15, 18)),
            news_seen_store_path=os.environ.get("NEWS_SEEN_STORE_PATH", "/app/data/bot-news-state.json").strip() or "/app/data/bot-news-state.json",
        )

    def is_group_allowed(self, group_id: str | None) -> bool:
        if self.qq_bot_allow_all_groups:
            return True
        if not group_id:
            return False
        return group_id in self.qq_bot_allowed_groups
