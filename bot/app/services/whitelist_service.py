from __future__ import annotations

from app.config import BotSettings


def is_group_allowed(settings: BotSettings, group_openid: str | None, group_id: str | None) -> bool:
    if settings.qq_bot_allow_all_groups:
        return True

    allowed = set(settings.qq_bot_allowed_groups)
    if not allowed:
        return False

    return bool((group_openid and group_openid in allowed) or (group_id and group_id in allowed))
