from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .models import CommandSpec


PAGE_PATTERN = re.compile(r"(?:第\s*)?(\d+)\s*页")
TRAILING_PAGE_PATTERN = re.compile(r"\bp\s*(\d+)$", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"(?:\bv|版本)\s*([A-Za-z0-9._-]+)", re.IGNORECASE)
STEP_PATTERN = re.compile(r"(?:(?:成长|预览)\s*)?\+([1-5])(?=\s|$)", re.IGNORECASE)
DAILY_REPORT_ALIASES = ("HEIGO日报", "heigo日报", "联赛日报", "今日联赛")
FULL_DATE_PATTERN = re.compile(r"^(\d{4})(?:年|[./-])(\d{1,2})(?:月|[./-])(\d{1,2})日?$")
MONTH_DAY_PATTERN = re.compile(r"^(\d{1,2})月(\d{1,2})日?$")
RELATIVE_REPORT_DATES = {"今天": 0, "今日": 0, "昨天": -1, "昨日": -1, "前天": -2}
LEAGUE_REPORT_ALIASES = {
    "league_standings": ("联赛积分榜", "联赛排名", "积分榜"),
    "league_suspensions": ("伤停统计", "联赛伤停", "伤停榜", "伤停"),
}
RATING_RANKING_ALIASES = ("排位排行榜", "排位积分榜", "排位榜", "排位")
PLAYER_RANKING_ALIASES = {
    "mvps": ("最佳球员榜", "MVP榜", "mvp榜", "最佳榜"),
    "assists": ("助攻排行榜", "助攻排行", "助攻榜"),
    "goals": ("球员数据榜", "球员排行榜", "射手榜", "进球榜", "球员榜"),
}


def _business_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _parse_report_date(value: str) -> tuple[str | None, str]:
    raw_value = re.sub(r"^(?:请|查询|查看|给我|返回|发一下)\s*", "", str(value or "").strip())
    raw_value = re.sub(r"\s*的\s*$", "", raw_value).strip()
    if not raw_value:
        return None, ""
    today = _business_today()
    if raw_value in RELATIVE_REPORT_DATES:
        return (today + timedelta(days=RELATIVE_REPORT_DATES[raw_value])).isoformat(), ""

    full_match = FULL_DATE_PATTERN.fullmatch(raw_value)
    month_day_match = MONTH_DAY_PATTERN.fullmatch(raw_value)
    try:
        if full_match:
            selected = date(int(full_match.group(1)), int(full_match.group(2)), int(full_match.group(3)))
        elif month_day_match:
            selected = date(today.year, int(month_day_match.group(1)), int(month_day_match.group(2)))
            if selected > today:
                selected = date(today.year - 1, selected.month, selected.day)
        else:
            return None, "日报日期格式无法识别，请使用“联赛日报 2026-08-02”或“联赛日报 8月2日”。"
    except ValueError:
        return None, "日报日期无效，请检查年月日是否正确。"
    if selected > today:
        return None, "日报日期不能晚于今天。"
    return selected.isoformat(), ""


def _parse_daily_report_command(working: str) -> tuple[bool, str | None, str]:
    lowered = working.casefold()
    for alias in DAILY_REPORT_ALIASES:
        alias_index = lowered.find(alias.casefold())
        if alias_index < 0:
            continue
        remainder = f"{working[:alias_index]} {working[alias_index + len(alias):]}".strip()
        report_date, date_error = _parse_report_date(remainder)
        return True, report_date, date_error
    return False, None, ""


def _parse_league_level(value: str) -> tuple[str | None, str]:
    normalized = re.sub(r"(?:请|查询|查看|给我|返回|发一下|发|一下|最新|当前|的|联赛|级别|情况|图)", "", str(value or ""))
    normalized = re.sub(r"\s+", "", normalized).strip()
    if not normalized:
        return "超级", ""
    aliases = {
        "超级": "超级", "超": "超级", "s": "超级",
        "甲级": "甲级", "甲": "甲级", "a": "甲级",
        "乙级": "乙级", "乙": "乙级", "b": "乙级",
    }
    level = aliases.get(normalized.casefold())
    if level:
        return level, ""
    return None, "联赛级别无法识别，目前支持“超级、甲级、乙级”。"


def _parse_league_report_command(working: str) -> tuple[str | None, str | None, str]:
    for command_type, aliases in LEAGUE_REPORT_ALIASES.items():
        for alias in aliases:
            index = working.find(alias)
            if index < 0:
                continue
            remainder = f"{working[:index]} {working[index + len(alias):]}".strip()
            level, error = _parse_league_level(remainder)
            return command_type, level, error
    return None, None, ""


def _parse_statistics_report_command(working: str) -> tuple[str | None, str | None, str, str]:
    for alias in RATING_RANKING_ALIASES:
        index = working.find(alias)
        if index < 0:
            continue
        remainder = f"{working[:index]} {working[index + len(alias):]}".strip()
        remainder = re.sub(r"(?:请|查询|查看|给我|返回|发一下|发|一下|最新|当前|的|全联盟|总榜|情况|图)", "", remainder)
        if not re.sub(r"\s+", "", remainder):
            return "rating_rankings", None, "goals", ""

    for metric, aliases in PLAYER_RANKING_ALIASES.items():
        for alias in aliases:
            index = working.find(alias)
            if index < 0:
                continue
            remainder = f"{working[:index]} {working[index + len(alias):]}".strip()
            level, error = _parse_league_level(remainder)
            return "player_rankings", level, metric, error

    for generic_alias in ("球员数据", "球员排行"):
        index = working.find(generic_alias)
        if index < 0:
            continue
        remainder = f"{working[:index]} {working[index + len(generic_alias):]}".strip()
        metric = "goals"
        for token, selected_metric in (("助攻", "assists"), ("最佳", "mvps"), ("MVP", "mvps"), ("mvp", "mvps"), ("进球", "goals"), ("射手", "goals")):
            if token in remainder:
                metric = selected_metric
                remainder = remainder.replace(token, " ")
                break
        level, error = _parse_league_level(remainder)
        return "player_rankings", level, metric, error
    return None, None, "goals", ""


def _extract_page(text: str) -> tuple[str, int]:
    match = PAGE_PATTERN.search(text)
    if not match:
        match = TRAILING_PAGE_PATTERN.search(text)
        if not match:
            return text, 1
    page = max(1, int(match.group(1)))
    return text[: match.start()].strip() + " " + text[match.end() :].strip(), page


def _extract_version(text: str) -> tuple[str, str | None]:
    match = VERSION_PATTERN.search(text)
    if not match:
        return text, None
    version = match.group(1).strip() or None
    return VERSION_PATTERN.sub(" ", text).strip(), version


def _extract_step(text: str) -> tuple[str, int]:
    match = STEP_PATTERN.search(text)
    if not match:
        return text, 0
    step = max(0, min(5, int(match.group(1))))
    return STEP_PATTERN.sub(" ", text, count=1).strip(), step


def parse_command(text: str) -> CommandSpec:
    normalized_text = " ".join((text or "").replace("\u3000", " ").split())
    working = normalized_text
    working, page = _extract_page(working)
    working, version = _extract_version(working)
    working, step = _extract_step(working)
    working = " ".join(working.split())

    if not working or working in {"帮助", "help", "?"}:
        return CommandSpec(command_type="help", raw_text=text, normalized_text=normalized_text, step=step, page=page, version=version)

    if working in {"新闻", "足球新闻", "懂球帝", "懂球帝新闻"}:
        return CommandSpec(command_type="football_news", raw_text=text, normalized_text=normalized_text, step=step, page=page, version=version)

    if working in {"早报", "足球早报", "懂球帝早报"}:
        return CommandSpec(command_type="football_daily", raw_text=text, normalized_text=normalized_text, step=step, page=page, version=version)

    is_daily_report, report_date, date_error = _parse_daily_report_command(working)
    if is_daily_report:
        return CommandSpec(
            command_type="heigo_daily_report",
            raw_text=text,
            normalized_text=normalized_text,
            step=step,
            page=page,
            version=version,
            report_date=report_date,
            date_error=date_error,
        )

    statistics_command_type, statistics_level, statistics_metric, statistics_error = _parse_statistics_report_command(working)
    if statistics_command_type:
        return CommandSpec(
            command_type=statistics_command_type,
            raw_text=text,
            normalized_text=normalized_text,
            step=step,
            page=page,
            version=version,
            level=statistics_level,
            level_error=statistics_error,
            metric=statistics_metric,
        )

    league_command_type, league_level, level_error = _parse_league_report_command(working)
    if league_command_type:
        return CommandSpec(
            command_type=league_command_type,
            raw_text=text,
            normalized_text=normalized_text,
            step=step,
            page=page,
            version=version,
            level=league_level,
            level_error=level_error,
        )

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
                step=step,
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
                step=step,
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
                step=step,
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
                step=step,
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
                step=step,
                page=page,
                version=version,
            )

    return CommandSpec(command_type="unknown", raw_text=text, normalized_text=normalized_text, keyword=working, step=step, page=page, version=version)
