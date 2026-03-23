from __future__ import annotations

import re

from .models import CommandSpec


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


def parse_command(text: str) -> CommandSpec:
    normalized_text = " ".join((text or "").replace("\u3000", " ").split())
    working = normalized_text
    working, page = _extract_page(working)
    working, version = _extract_version(working)
    working = " ".join(working.split())

    if not working or working in {"帮助", "help", "?"}:
        return CommandSpec(command_type="help", raw_text=text, normalized_text=normalized_text, page=page, version=version)

    for prefix in ("球员图", "球员"):
        if working.startswith(prefix):
            keyword = working.removeprefix(prefix).strip()
            uid = int(keyword) if keyword.isdigit() else None
            return CommandSpec(
                command_type="player_image",
                raw_text=text,
                normalized_text=normalized_text,
                keyword=keyword,
                uid=uid,
                page=page,
                version=version,
            )

    for prefix in ("工资图",):
        if working.startswith(prefix):
            keyword = working.removeprefix(prefix).strip()
            uid = int(keyword) if keyword.isdigit() else None
            return CommandSpec(
                command_type="wage_image",
                raw_text=text,
                normalized_text=normalized_text,
                keyword=keyword,
                uid=uid,
                page=page,
                version=version,
            )

    for prefix in ("工资",):
        if working.startswith(prefix):
            keyword = working.removeprefix(prefix).strip()
            uid = int(keyword) if keyword.isdigit() else None
            return CommandSpec(
                command_type="wage_text",
                raw_text=text,
                normalized_text=normalized_text,
                keyword=keyword,
                uid=uid,
                page=page,
                version=version,
            )

    for prefix in ("名单图",):
        if working.startswith(prefix):
            team_name = working.removeprefix(prefix).strip()
            return CommandSpec(
                command_type="roster_image",
                raw_text=text,
                normalized_text=normalized_text,
                team_name=team_name,
                page=page,
                version=version,
            )

    for prefix in ("名单",):
        if working.startswith(prefix):
            team_name = working.removeprefix(prefix).strip()
            return CommandSpec(
                command_type="roster_text",
                raw_text=text,
                normalized_text=normalized_text,
                team_name=team_name,
                page=page,
                version=version,
            )

    return CommandSpec(command_type="unknown", raw_text=text, normalized_text=normalized_text, keyword=working, page=page, version=version)
