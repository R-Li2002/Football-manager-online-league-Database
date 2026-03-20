from __future__ import annotations

import re

from app.schemas.bot_commands import BotCommand
from app.utils.text import strip_robot_mentions


PAGE_PATTERN = re.compile(r"第\s*(\d+)\s*页")
VERSION_PATTERN = re.compile(r"(?:\bv|版本)\s*([A-Za-z0-9._-]+)", re.IGNORECASE)


def _extract_page(text: str) -> tuple[str, int]:
    match = PAGE_PATTERN.search(text)
    if not match:
        return text, 1
    page = max(1, int(match.group(1)))
    return PAGE_PATTERN.sub(" ", text).strip(), page


def _extract_version(text: str) -> tuple[str, str | None]:
    match = VERSION_PATTERN.search(text)
    if not match:
        return text, None
    version = match.group(1).strip() or None
    return VERSION_PATTERN.sub(" ", text).strip(), version


def parse_command(text: str) -> BotCommand:
    normalized_text = strip_robot_mentions(text)
    working = normalized_text
    working, page = _extract_page(working)
    working, version = _extract_version(working)
    working = " ".join(working.split())

    if not working or working in {"帮助", "help", "?"}:
        return BotCommand(command_type="help", raw_text=text, normalized_text=normalized_text, page=page, version=version)

    if working.startswith("球员图"):
        keyword = working.removeprefix("球员图").strip()
        uid = int(keyword) if keyword.isdigit() else None
        return BotCommand(
            command_type="player_image",
            raw_text=text,
            normalized_text=normalized_text,
            keyword=keyword,
            uid=uid,
            page=page,
            version=version,
        )

    if working.startswith("球员") or working.startswith("查人"):
        keyword = working.removeprefix("球员").strip() if working.startswith("球员") else working.removeprefix("查人").strip()
        uid = int(keyword) if keyword.isdigit() else None
        return BotCommand(
            command_type="player",
            raw_text=text,
            normalized_text=normalized_text,
            keyword=keyword,
            uid=uid,
            page=page,
            version=version,
        )

    if working.startswith("名单"):
        team_name = working.removeprefix("名单").strip()
        return BotCommand(
            command_type="roster",
            raw_text=text,
            normalized_text=normalized_text,
            team_name=team_name,
            page=page,
            version=version,
        )

    if working.startswith("工资"):
        keyword = working.removeprefix("工资").strip()
        uid = int(keyword) if keyword.isdigit() else None
        return BotCommand(
            command_type="wage",
            raw_text=text,
            normalized_text=normalized_text,
            keyword=keyword,
            uid=uid,
            page=page,
            version=version,
        )

    return BotCommand(command_type="unknown", raw_text=text, normalized_text=normalized_text, keyword=working, page=page, version=version)
