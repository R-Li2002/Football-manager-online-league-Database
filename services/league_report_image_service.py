from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from html import escape
import json
from pathlib import Path
from typing import Any

try:
    import cairosvg
except ImportError:  # pragma: no cover - runtime dependency
    cairosvg = None

from schemas_read import PlayerRankingsResponse, RankingsResponse, StandingsResponse, SuspensionsResponse
from services.team_name_service import common_chinese_team_name


IMAGE_WIDTH = 1200
SIDE_PADDING = 64
CONTENT_WIDTH = IMAGE_WIDTH - SIDE_PADDING * 2
TEMPLATE_VERSION = 2

# Keep the server-rendered QQ images on the same Tokyo Night / glass surface
# language as the main site. Level accents mirror `.league-level-signature`.
LEVEL_COLORS = {"超级": "#9C82FF", "甲级": "#55AEFF", "乙级": "#45CF9A", "HEIGO": "#7AA2F7"}
LEVEL_META = {
    "超级": ("S", "SUPER"),
    "甲级": ("A", "FIRST"),
    "乙级": ("B", "SECOND"),
    "HEIGO": ("H", "RATING"),
}
BG_TOP = "#16161E"
BG_MIDDLE = "#1F2335"
BG_BOTTOM = "#24283B"
SURFACE_STRONG = "#1F2335"
SURFACE_MUTED = "#292E42"
TEXT_PRIMARY = "#D7DEFE"
TEXT_SECONDARY = "#B6C0E6"
ACCENT_PRIMARY = "#7AA2F7"
ACCENT_SECONDARY = "#BB9AF7"
SUCCESS = "#57D5A1"
WARNING = "#E8B86D"
DANGER = "#F27D92"


@dataclass(frozen=True)
class RenderedLeagueReportPng:
    file_path: str
    file_name: str
    etag: str
    cache_status: str


def _text_units(value: str) -> int:
    return sum(1 if ord(char) < 128 else 2 for char in str(value or ""))


def _wrap_text(value: str, max_units: int) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    lines: list[str] = []
    current = ""
    current_units = 0
    for char in text:
        units = 1 if ord(char) < 128 else 2
        if current and current_units + units > max_units:
            lines.append(current.rstrip())
            current = ""
            current_units = 0
        current += char
        current_units += units
    if current:
        lines.append(current.rstrip())
    return lines


def _truncate_text(value: str, max_units: int) -> str:
    text = str(value or "").strip()
    if _text_units(text) <= max_units:
        return text
    target = max(1, max_units - 2)
    result = ""
    units = 0
    for char in text:
        char_units = 1 if ord(char) < 128 else 2
        if units + char_units > target:
            break
        result += char
        units += char_units
    return f"{result.rstrip()}…"


def _base_svg_parts(
    height: int,
    *,
    eyebrow: str,
    title: str,
    subtitle: str,
    level: str,
    status_label: str,
) -> list[str]:
    accent = LEVEL_COLORS.get(level, ACCENT_PRIMARY)
    mark, english = LEVEL_META.get(level, ("L", "LEAGUE"))
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{IMAGE_WIDTH}" height="{height}" viewBox="0 0 {IMAGE_WIDTH} {height}">',
        '<defs>',
        f'<linearGradient id="siteBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_TOP}"/><stop offset="0.48" stop-color="{BG_MIDDLE}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>',
        f'<linearGradient id="sitePanel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{SURFACE_STRONG}"/><stop offset="1" stop-color="{SURFACE_MUTED}"/></linearGradient>',
        f'<linearGradient id="siteAccent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT_PRIMARY}"/><stop offset="1" stop-color="{ACCENT_SECONDARY}"/></linearGradient>',
        f'<radialGradient id="siteGlowBlue"><stop offset="0" stop-color="{ACCENT_PRIMARY}" stop-opacity="0.18"/><stop offset="1" stop-color="{ACCENT_PRIMARY}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="siteGlowPurple"><stop offset="0" stop-color="{ACCENT_SECONDARY}" stop-opacity="0.14"/><stop offset="1" stop-color="{ACCENT_SECONDARY}" stop-opacity="0"/></radialGradient>',
        '<filter id="siteShadow" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="16" stdDeviation="22" flood-color="#050814" flood-opacity="0.28"/></filter>',
        '</defs>',
        f'<rect width="{IMAGE_WIDTH}" height="{height}" fill="url(#siteBg)"/>',
        '<ellipse cx="210" cy="4" rx="430" ry="260" fill="url(#siteGlowBlue)"/>',
        '<ellipse cx="1090" cy="28" rx="330" ry="240" fill="url(#siteGlowPurple)"/>',
        f'<rect x="24" y="24" width="1152" height="{height - 48}" rx="28" fill="{SURFACE_STRONG}" fill-opacity="0.78" stroke="#C0CAF5" stroke-opacity="0.10" filter="url(#siteShadow)"/>',
        '<rect x="24" y="24" width="1152" height="4" rx="2" fill="url(#siteAccent)"/>',
        f'<text x="{SIDE_PADDING}" y="67" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="900" letter-spacing="2.6" fill="{ACCENT_PRIMARY}">{escape(eyebrow)}</text>',
        f'<text x="{SIDE_PADDING}" y="122" font-family="Noto Sans CJK SC, sans-serif" font-size="39" font-weight="900" fill="{TEXT_PRIMARY}">{escape(title)}</text>',
        f'<text x="{SIDE_PADDING}" y="158" font-family="Noto Sans CJK SC, sans-serif" font-size="16" font-weight="600" fill="{TEXT_SECONDARY}">{escape(subtitle)}</text>',
        f'<rect x="956" y="52" width="180" height="58" rx="16" fill="{accent}" fill-opacity="0.08" stroke="{accent}" stroke-opacity="0.34"/>',
        f'<rect x="966" y="61" width="40" height="40" rx="11" fill="{accent}" fill-opacity="0.12" stroke="{accent}" stroke-opacity="0.52"/>',
        f'<text x="986" y="88" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="18" font-weight="950" fill="{accent}">{mark}</text>',
        f'<rect x="978" y="93" width="16" height="2.5" rx="1.25" fill="{accent}" opacity="0.72"/>',
        f'<text x="1020" y="76" font-family="Noto Sans CJK SC, sans-serif" font-size="14" font-weight="900" fill="{TEXT_PRIMARY}">{escape(level)}</text>',
        f'<text x="1020" y="95" font-family="DejaVu Sans, sans-serif" font-size="9" font-weight="850" letter-spacing="1.5" fill="{accent}">{english}</text>',
        f'<rect x="986" y="132" width="150" height="32" rx="16" fill="{accent}" fill-opacity="0.10" stroke="{accent}" stroke-opacity="0.24"/>',
        f'<text x="1061" y="153" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="850" fill="{accent}">{escape(status_label)}</text>',
        '<line x1="64" y1="188" x2="1136" y2="188" stroke="#C0CAF5" stroke-opacity="0.10"/>',
    ]


def _footer(parts: list[str], height: int, level: str) -> None:
    parts.extend([
        f'<line x1="{SIDE_PADDING}" y1="{height - 67}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{height - 67}" stroke="#C0CAF5" stroke-opacity="0.10"/>',
        f'<text x="{SIDE_PADDING}" y="{height - 33}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="700" fill="#7F89AD">HEIGO 联机联赛数据库 · 与主站使用同一实时数据</text>',
        f'<text x="{IMAGE_WIDTH - SIDE_PADDING}" y="{height - 33}" text-anchor="end" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="700" fill="#7F89AD">{escape(level)} · HEIGO LEAGUE DATA HUB</text>',
        '</svg>',
    ])


def _prediction_tone(row: Any, total: int) -> str:
    predicted = int(row.predicted_rank or row.rank or 1)
    if predicted <= 5:
        return SUCCESS
    if predicted > max(0, total - 5):
        return DANGER
    return ACCENT_SECONDARY


def _build_standings_svg(standings: StandingsResponse, level: str) -> str:
    rows = [row for row in standings.rows if row.level == level]
    summary = next((item for item in standings.prediction_summaries if item.level == level), None)
    accent = LEVEL_COLORS.get(level, ACCENT_PRIMARY)
    row_height = 50
    table_y = 288
    table_header_height = 46
    height = max(820, table_y + table_header_height + len(rows) * row_height + 98)
    if summary and summary.total_match_count:
        progress = round(float(summary.progress or 0) * 100)
        subtitle = f"{summary.phase_label} · 赛程完成 {progress}% · {summary.played_match_count}/{summary.total_match_count} 场"
        simulation_label = f"{int(summary.simulations):,} 次赛季模拟" if summary.simulations else "最终排名已确定"
        prediction_copy = f"{simulation_label} · {summary.interval_label}"
        phase_label = summary.phase_label
    else:
        progress = 0
        subtitle = "赛程待完整导入 · 当前仅展示实时积分排名"
        prediction_copy = "完整赛程导入后，将按真实对阵持续模拟并逐轮收束"
        phase_label = "排名预测待启动"
    parts = _base_svg_parts(
        height,
        eyebrow="HEIGO LEAGUE DATA HUB / STANDINGS",
        title=f"{level}积分榜",
        subtitle=subtitle,
        level=level,
        status_label="实时积分与排名预测",
    )
    parts.extend([
        f'<rect x="{SIDE_PADDING}" y="210" width="{CONTENT_WIDTH}" height="58" rx="14" fill="{SURFACE_MUTED}" fill-opacity="0.72" stroke="#C0CAF5" stroke-opacity="0.10"/>',
        f'<rect x="{SIDE_PADDING}" y="210" width="4" height="58" rx="2" fill="{accent}"/>',
        f'<text x="84" y="235" font-family="Noto Sans CJK SC, sans-serif" font-size="15" font-weight="900" fill="{TEXT_PRIMARY}">{escape(phase_label)}</text>',
        f'<text x="84" y="256" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="600" fill="{TEXT_SECONDARY}">{escape(prediction_copy)}</text>',
        '<rect x="748" y="232" width="246" height="7" rx="3.5" fill="#16161E" fill-opacity="0.82"/>',
        f'<rect x="748" y="232" width="{max(4, round(246 * progress / 100))}" height="7" rx="3.5" fill="url(#siteAccent)"/>',
        f'<text x="1008" y="241" font-family="DejaVu Sans, sans-serif" font-size="12" font-weight="850" fill="{ACCENT_PRIMARY}">{progress}%</text>',
        f'<rect x="1048" y="222" width="74" height="26" rx="13" fill="{SUCCESS}" fill-opacity="0.10" stroke="{SUCCESS}" stroke-opacity="0.24"/>',
        f'<text x="1085" y="239" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="850" fill="{SUCCESS}">前五区</text>',
        f'<rect x="1048" y="250" width="74" height="26" rx="13" fill="{DANGER}" fill-opacity="0.10" stroke="{DANGER}" stroke-opacity="0.24"/>',
        f'<text x="1085" y="267" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="850" fill="{DANGER}">后五区</text>',
        f'<rect x="{SIDE_PADDING}" y="{table_y}" width="{CONTENT_WIDTH}" height="{table_header_height + len(rows) * row_height}" rx="16" fill="{SURFACE_STRONG}" fill-opacity="0.74" stroke="#C0CAF5" stroke-opacity="0.11"/>',
        f'<path d="M{SIDE_PADDING + 16} {table_y}H{IMAGE_WIDTH - SIDE_PADDING - 16}Q{IMAGE_WIDTH - SIDE_PADDING} {table_y} {IMAGE_WIDTH - SIDE_PADDING} {table_y + 16}V{table_y + table_header_height}H{SIDE_PADDING}V{table_y + 16}Q{SIDE_PADDING} {table_y} {SIDE_PADDING + 16} {table_y}Z" fill="{ACCENT_PRIMARY}" fill-opacity="0.12"/>',
    ])
    headers = (
        ("排名", 96, "middle"), ("球队", 140, "start"), ("主教练", 395, "start"),
        ("场", 548, "middle"), ("胜", 605, "middle"), ("平", 658, "middle"),
        ("负", 711, "middle"), ("进", 766, "middle"), ("失", 821, "middle"),
        ("净", 878, "middle"), ("积分", 945, "middle"), ("预测排名", 1064, "middle"),
    )
    for label, x, anchor in headers:
        parts.append(f'<text x="{x}" y="{table_y + 29}" text-anchor="{anchor}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="850" fill="{TEXT_PRIMARY}">{label}</text>')

    total = len(rows)
    for index, row in enumerate(rows):
        y = table_y + table_header_height + index * row_height
        rank = int(row.rank or index + 1)
        is_top = rank <= 5
        is_bottom = rank > max(0, total - 5)
        zone_color = SUCCESS if is_top else DANGER if is_bottom else accent
        if is_top:
            row_fill, row_opacity = SUCCESS, 0.075
        elif is_bottom:
            row_fill, row_opacity = DANGER, 0.065
        else:
            row_fill, row_opacity = SURFACE_MUTED, 0.34 if index % 2 else 0.18
        team_name = _truncate_text(common_chinese_team_name(row.team_name), 25)
        manager = _truncate_text(row.manager or "待定", 16)
        goal_difference = int(row.goal_difference or 0)
        predicted = int(row.predicted_rank or rank)
        predicted_min = int(row.predicted_rank_min or rank)
        predicted_max = int(row.predicted_rank_max or rank)
        prediction_range = f"{predicted_min}–{predicted_max}"
        prediction_color = _prediction_tone(row, total)
        parts.extend([
            f'<rect x="{SIDE_PADDING}" y="{y}" width="{CONTENT_WIDTH}" height="{row_height}" fill="{row_fill}" fill-opacity="{row_opacity}"/>',
            f'<rect x="{SIDE_PADDING}" y="{y}" width="4" height="{row_height}" fill="{zone_color}" fill-opacity="0.9"/>',
            f'<line x1="{SIDE_PADDING}" y1="{y + row_height}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{y + row_height}" stroke="#C0CAF5" stroke-opacity="0.075"/>',
            f'<text x="96" y="{y + 32}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="16" font-weight="900" fill="{zone_color}">{rank}</text>',
            f'<text x="140" y="{y + 32}" font-family="Noto Sans CJK SC, sans-serif" font-size="16" font-weight="850" fill="{TEXT_PRIMARY}">{escape(team_name)}</text>',
            f'<text x="395" y="{y + 31}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="650" fill="{TEXT_SECONDARY}">{escape(manager)}</text>',
            f'<text x="548" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.played or 0)}</text>',
            f'<text x="605" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.wins or 0)}</text>',
            f'<text x="658" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.draws or 0)}</text>',
            f'<text x="711" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.losses or 0)}</text>',
            f'<text x="766" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.goals_for or 0)}</text>',
            f'<text x="821" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.goals_against or 0)}</text>',
            f'<text x="878" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="800" fill="{TEXT_SECONDARY}">{"+" if goal_difference > 0 else ""}{goal_difference}</text>',
            f'<text x="945" y="{y + 32}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="17" font-weight="950" fill="{ACCENT_PRIMARY}">{int(row.points or 0)}</text>',
            f'<text x="1042" y="{y + 30}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="16" font-weight="950" fill="{prediction_color}">{predicted}</text>',
            f'<text x="1092" y="{y + 30}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="10" font-weight="750" fill="#8E99BF">{prediction_range}</text>',
        ])
    _footer(parts, height, level)
    return "".join(parts)


def _player_status(player: Any) -> str:
    labels: list[str] = []
    if bool(player.yellow_card_suspended):
        labels.append("3黄停赛")
    if int(player.yellow_cards or 0) > 0:
        labels.append(f"额外{int(player.yellow_cards)}黄")
    if bool(player.red_card_suspended):
        labels.append("红牌停赛")
    if bool(player.red_injury_suspended):
        labels.append("红伤停赛")
    if bool(player.yellow_card_suspended) or bool(player.red_card_suspended) or bool(player.red_injury_suspended):
        total = max(1, int(player.suspension_matches or 1))
        remaining = max(0, int(player.suspension_remaining_matches or total))
        labels.append(f"停赛{total}场" + (f" / 剩余{remaining}场" if remaining < total else ""))
    if player.notes:
        labels.append(str(player.notes).strip())
    return "、".join(labels) or "状态关注"


def _suspension_sections(team: Any) -> list[tuple[str, list[Any], str]]:
    return [
        ("1张黄牌", list(team.one_yellow or []), WARNING),
        ("2张黄牌", list(team.two_yellows or []), "#F3A95F"),
        ("停赛", list(team.suspended or []), DANGER),
    ]


def _suspension_card_data(team: Any) -> dict[str, Any]:
    sections = [(label, players, color) for label, players, color in _suspension_sections(team) if players]
    progress = team.progress
    abnormal = bool(progress and progress.state in {"stale", "gap", "unknown"})
    progress_copy = ""
    if abnormal and progress:
        progress_copy = " · ".join(part for part in (str(progress.title or "").strip(), str(progress.detail or "").strip()) if part)
    progress_lines = _wrap_text(progress_copy, 40)[:2]
    note_text = "；".join(str(note).strip() for note in (team.notes or []) if str(note).strip())
    note_lines = _wrap_text(note_text, 40)[:2]
    section_heights = [max(48, 16 + len(players) * 32) for _, players, _ in sections]
    body_height = sum(height + 8 for height in section_heights)
    if not sections:
        body_height += 48
    if progress_lines:
        body_height += 18 + len(progress_lines) * 17
    if note_lines:
        body_height += 18 + len(note_lines) * 17
    return {
        "team": team,
        "sections": sections,
        "section_heights": section_heights,
        "progress_lines": progress_lines,
        "note_lines": note_lines,
        "height": 76 + body_height + 14,
    }


def _progress_badge(progress: Any) -> tuple[str, str]:
    if not progress:
        return "轮次待补", TEXT_SECONDARY
    checked = progress.suspension_checked_round
    applies = progress.applies_from_round
    if checked is not None and applies is not None:
        label = f"第{checked}轮 → 第{applies}轮"
    elif checked is not None:
        label = f"核对至第{checked}轮"
    else:
        label = _truncate_text(progress.title or "轮次待补", 14)
    color = SUCCESS if progress.state in {"current", "ahead"} else DANGER if progress.state in {"stale", "gap"} else TEXT_SECONDARY
    return label, color


def _render_suspension_card(parts: list[str], item: dict[str, Any], x: float, y: float, width: float) -> None:
    team = item["team"]
    height = int(item["height"])
    badge_label, badge_color = _progress_badge(team.progress)
    team_name = _truncate_text(common_chinese_team_name(team.team_name), 22)
    manager = _truncate_text(team.manager or "主教练待定", 20)
    parts.extend([
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height}" rx="16" fill="{SURFACE_MUTED}" fill-opacity="0.70" stroke="#C0CAF5" stroke-opacity="0.10"/>',
        f'<text x="{x + 14:.1f}" y="{y + 28:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="17" font-weight="900" fill="{TEXT_PRIMARY}">{escape(team_name)}</text>',
        f'<text x="{x + 14:.1f}" y="{y + 48:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="600" fill="{TEXT_SECONDARY}">{escape(manager)}</text>',
        f'<rect x="{x + width - 102:.1f}" y="{y + 15:.1f}" width="88" height="25" rx="12.5" fill="{badge_color}" fill-opacity="0.10" stroke="{badge_color}" stroke-opacity="0.22"/>',
        f'<text x="{x + width - 58:.1f}" y="{y + 32:.1f}" text-anchor="middle" font-family="DejaVu Sans, Noto Sans CJK SC, sans-serif" font-size="10" font-weight="850" fill="{badge_color}">{escape(badge_label)}</text>',
        f'<line x1="{x + 14:.1f}" y1="{y + 62:.1f}" x2="{x + width - 14:.1f}" y2="{y + 62:.1f}" stroke="#C0CAF5" stroke-opacity="0.10"/>',
    ])
    cursor_y = y + 74
    for section_index, (label, players, color) in enumerate(item["sections"]):
        section_height = item["section_heights"][section_index]
        parts.extend([
            f'<rect x="{x + 12:.1f}" y="{cursor_y:.1f}" width="{width - 24:.1f}" height="{section_height}" rx="11" fill="{color}" fill-opacity="0.075" stroke="{color}" stroke-opacity="0.16"/>',
            f'<rect x="{x + 18:.1f}" y="{cursor_y + 7:.1f}" width="68" height="{section_height - 14}" rx="9" fill="{color}" fill-opacity="0.12"/>',
            f'<text x="{x + 52:.1f}" y="{cursor_y + section_height / 2 + 4:.1f}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="900" fill="{color}">{escape(label)}</text>',
        ])
        player_y = cursor_y + 21
        for player in players:
            name = _truncate_text(player.player_name, 18)
            status = _truncate_text(_player_status(player), 12)
            parts.extend([
                f'<text x="{x + 98:.1f}" y="{player_y:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="850" fill="{TEXT_PRIMARY}">{escape(name)}</text>',
                f'<text x="{x + width - 18:.1f}" y="{player_y:.1f}" text-anchor="end" font-family="Noto Sans CJK SC, sans-serif" font-size="9" font-weight="700" fill="{TEXT_SECONDARY}">{escape(status)}</text>',
            ])
            player_y += 32
        cursor_y += section_height + 8
    if not item["sections"]:
        parts.extend([
            f'<rect x="{x + 12:.1f}" y="{cursor_y:.1f}" width="{width - 24:.1f}" height="40" rx="10" fill="{DANGER}" fill-opacity="0.065" stroke="{DANGER}" stroke-opacity="0.14"/>',
            f'<text x="{x + 26:.1f}" y="{cursor_y + 25:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="700" fill="{TEXT_SECONDARY}">暂无登记球员，因核对进度列入提醒</text>',
        ])
        cursor_y += 48
    if item["progress_lines"]:
        parts.append(f'<text x="{x + 14:.1f}" y="{cursor_y + 12:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="9" font-weight="900" fill="{DANGER}">进度提醒</text>')
        cursor_y += 29
        for line in item["progress_lines"]:
            parts.append(f'<text x="{x + 14:.1f}" y="{cursor_y:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="600" fill="{TEXT_SECONDARY}">{escape(line)}</text>')
            cursor_y += 17
    if item["note_lines"]:
        parts.append(f'<text x="{x + 14:.1f}" y="{cursor_y + 12:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="9" font-weight="900" fill="{ACCENT_PRIMARY}">球队备注</text>')
        cursor_y += 29
        for line in item["note_lines"]:
            parts.append(f'<text x="{x + 14:.1f}" y="{cursor_y:.1f}" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="600" fill="{TEXT_SECONDARY}">{escape(line)}</text>')
            cursor_y += 17


def _build_suspensions_svg(suspensions: SuspensionsResponse, level: str) -> str:
    teams = [team for team in suspensions.teams if team.level == level]
    active_teams = [team for team in teams if team.one_yellow or team.two_yellows or team.suspended]
    progress_teams = [team for team in teams if team.progress and team.progress.state in {"stale", "gap", "unknown"}]
    display_teams: list[Any] = []
    seen_team_ids: set[int] = set()
    for team in (*active_teams, *progress_teams):
        if int(team.team_id) in seen_team_ids:
            continue
        seen_team_ids.add(int(team.team_id))
        display_teams.append(team)
    caution_players = sum(len(team.one_yellow) + len(team.two_yellows) for team in teams)
    suspended_players = sum(len(team.suspended) for team in teams)
    abnormal_count = sum(1 for team in teams if team.progress and team.progress.state in {"stale", "gap", "unknown"})
    prepared = [_suspension_card_data(team) for team in display_teams]
    clear_teams = [team for team in teams if int(team.team_id) not in seen_team_ids]
    clear_names = "、".join(common_chinese_team_name(team.team_name) for team in clear_teams)
    clear_lines = _wrap_text(clear_names, 108)

    content_y = 316
    column_gap = 12
    column_width = (CONTENT_WIDTH - column_gap * 2) / 3
    row_heights: list[int] = []
    for index in range(0, len(prepared), 3):
        row_heights.append(max(item["height"] for item in prepared[index:index + 3]))
    cards_height = sum(row_heights) + max(0, len(row_heights) - 1) * 12
    if not prepared:
        cards_height = 142
    clear_footer_height = 0
    if clear_teams and prepared:
        clear_footer_height = 48 + len(clear_lines) * 17
    content_height = cards_height + (14 + clear_footer_height if clear_footer_height else 0)
    height = max(820, content_y + content_height + 98)
    subtitle = f"伤停核对以主站实时轮次为准 · {len(active_teams)} 队有记录 · {abnormal_count} 队需确认进度"
    parts = _base_svg_parts(
        height,
        eyebrow="HEIGO DISCIPLINE REPORT",
        title=f"{level}伤停统计",
        subtitle=subtitle,
        level=level,
        status_label=f"{len(active_teams)} 队有记录" if active_teams else "本轮无伤停记录",
    )
    stats = (
        ("参赛球队", len(teams), TEXT_PRIMARY),
        ("黄牌关注", caution_players, WARNING),
        ("停赛球员", suspended_players, DANGER),
        ("进度待确认", abnormal_count, DANGER if abnormal_count else SUCCESS),
    )
    stat_gap = 10
    stat_width = (CONTENT_WIDTH - stat_gap * 3) / 4
    for index, (label, value, color) in enumerate(stats):
        x = SIDE_PADDING + index * (stat_width + stat_gap)
        parts.extend([
            f'<rect x="{x:.1f}" y="210" width="{stat_width:.1f}" height="80" rx="14" fill="{SURFACE_MUTED}" fill-opacity="0.70" stroke="#C0CAF5" stroke-opacity="0.10"/>',
            f'<text x="{x + 14:.1f}" y="235" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="800" fill="{TEXT_SECONDARY}">{escape(label)}</text>',
            f'<text x="{x + 14:.1f}" y="272" font-family="DejaVu Sans, sans-serif" font-size="27" font-weight="950" fill="{color}">{value}</text>',
        ])

    if not prepared:
        parts.extend([
            f'<rect x="{SIDE_PADDING}" y="{content_y}" width="{CONTENT_WIDTH}" height="142" rx="18" fill="{SUCCESS}" fill-opacity="0.06" stroke="{SUCCESS}" stroke-opacity="0.24" stroke-dasharray="7 7"/>',
            f'<circle cx="{IMAGE_WIDTH / 2}" cy="{content_y + 46}" r="16" fill="{SUCCESS}" fill-opacity="0.12" stroke="{SUCCESS}" stroke-opacity="0.55"/>',
            f'<path d="M590 {content_y + 46}l7 7 14-16" fill="none" stroke="{SUCCESS}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<text x="{IMAGE_WIDTH / 2}" y="{content_y + 91}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="20" font-weight="900" fill="{SUCCESS}">当前没有黄牌关注或停赛记录</text>',
            f'<text x="{IMAGE_WIDTH / 2}" y="{content_y + 118}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="600" fill="{TEXT_SECONDARY}">全部 {len(teams)} 支球队均无伤停记录</text>',
        ])
    else:
        y = content_y
        item_index = 0
        for row_height in row_heights:
            row_items = prepared[item_index:item_index + 3]
            for column_index, item in enumerate(row_items):
                x = SIDE_PADDING + column_index * (column_width + column_gap)
                _render_suspension_card(parts, item, x, y, column_width)
            item_index += len(row_items)
            y += row_height + 12
        y -= 12
        if clear_footer_height:
            y += 14
            parts.extend([
                f'<rect x="{SIDE_PADDING}" y="{y}" width="{CONTENT_WIDTH}" height="{clear_footer_height}" rx="14" fill="{SUCCESS}" fill-opacity="0.055" stroke="{SUCCESS}" stroke-opacity="0.18"/>',
                f'<text x="82" y="{y + 25}" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="900" fill="{SUCCESS}">暂无记录球队 · {len(clear_teams)}</text>',
            ])
            line_y = y + 48
            for line in clear_lines:
                parts.append(f'<text x="82" y="{line_y}" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="600" fill="{TEXT_SECONDARY}">{escape(line)}</text>')
                line_y += 17
    _footer(parts, height, level)
    return "".join(parts)


def _format_points(value: Any) -> str:
    number = round(float(value or 0), 4)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.4f}".rstrip("0").rstrip(".")


def _build_rankings_svg(rankings: RankingsResponse) -> str:
    rows = list(rankings.rows or [])
    row_height = 42
    table_y = 318
    table_header_height = 46
    height = max(900, table_y + table_header_height + len(rows) * row_height + 98)
    subtitle = (
        f"胜者取得败者赛前基础分的 {float(rankings.transfer_rate or 0) * 100:g}%"
        f" · 每完成一场总分另加 {_format_points(rankings.appearance_bonus)}"
    )
    cutoff_label = f" · 截止排位贴第{int(rankings.cutoff_floor)}楼" if rankings.cutoff_floor else ""
    parts = _base_svg_parts(
        height,
        eyebrow="HEIGO RATING DESK",
        title="排位积分榜",
        subtitle=subtitle,
        level="HEIGO",
        status_label=f"{len(rows)} 支球队 · {int(rankings.total_matches or 0)} 场赛果{cutoff_label}",
    )
    rule_items = (
        ("初始基础分", _format_points(rankings.initial_points), "BASE RATING", ACCENT_PRIMARY),
        ("胜负转移", f"{float(rankings.transfer_rate or 0) * 100:g}%", "TRANSFER", ACCENT_SECONDARY),
        ("每场奖励", f"+{_format_points(rankings.appearance_bonus)}", "MATCH BONUS", SUCCESS),
    )
    rule_gap = 10
    rule_width = (CONTENT_WIDTH - rule_gap * 2) / 3
    for index, (label, value, english, color) in enumerate(rule_items):
        x = SIDE_PADDING + index * (rule_width + rule_gap)
        parts.extend([
            f'<rect x="{x:.1f}" y="210" width="{rule_width:.1f}" height="82" rx="15" fill="{SURFACE_MUTED}" fill-opacity="0.70" stroke="#C0CAF5" stroke-opacity="0.10"/>',
            f'<rect x="{x:.1f}" y="210" width="4" height="82" rx="2" fill="{color}"/>',
            f'<text x="{x + 18:.1f}" y="234" font-family="DejaVu Sans, sans-serif" font-size="9" font-weight="900" letter-spacing="1.3" fill="{color}">{english}</text>',
            f'<text x="{x + 18:.1f}" y="256" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="700" fill="{TEXT_SECONDARY}">{escape(label)}</text>',
            f'<text x="{x + rule_width - 18:.1f}" y="267" text-anchor="end" font-family="DejaVu Sans, sans-serif" font-size="25" font-weight="950" fill="{TEXT_PRIMARY}">{escape(value)}</text>',
        ])
    table_height = table_header_height + len(rows) * row_height
    parts.extend([
        f'<rect x="{SIDE_PADDING}" y="{table_y}" width="{CONTENT_WIDTH}" height="{table_height}" rx="16" fill="{SURFACE_STRONG}" fill-opacity="0.74" stroke="#C0CAF5" stroke-opacity="0.11"/>',
        f'<path d="M{SIDE_PADDING + 16} {table_y}H{IMAGE_WIDTH - SIDE_PADDING - 16}Q{IMAGE_WIDTH - SIDE_PADDING} {table_y} {IMAGE_WIDTH - SIDE_PADDING} {table_y + 16}V{table_y + table_header_height}H{SIDE_PADDING}V{table_y + 16}Q{SIDE_PADDING} {table_y} {SIDE_PADDING + 16} {table_y}Z" fill="{ACCENT_PRIMARY}" fill-opacity="0.12"/>',
    ])
    headers = (
        ("排名", 98, "middle"), ("球队", 142, "start"), ("级别", 506, "middle"),
        ("基础分", 650, "middle"), ("总分", 790, "middle"), ("场次", 910, "middle"),
        ("胜 / 平 / 负", 1040, "middle"),
    )
    for label, x, anchor in headers:
        parts.append(f'<text x="{x}" y="{table_y + 29}" text-anchor="{anchor}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="850" fill="{TEXT_PRIMARY}">{label}</text>')
    podium_colors = {1: "#D9AA31", 2: "#9AA7B5", 3: "#B77B4A"}
    for index, row in enumerate(rows):
        y = table_y + table_header_height + index * row_height
        rank = int(row.rank or index + 1)
        level = str(row.level or "")
        level_color = LEVEL_COLORS.get(level, ACCENT_PRIMARY)
        level_mark = LEVEL_META.get(level, ("L", ""))[0]
        podium_color = podium_colors.get(rank)
        row_fill = podium_color if podium_color else SURFACE_MUTED
        row_opacity = 0.075 if podium_color else (0.28 if index % 2 else 0.14)
        team_name = _truncate_text(common_chinese_team_name(row.team_name), 31)
        parts.extend([
            f'<rect x="{SIDE_PADDING}" y="{y}" width="{CONTENT_WIDTH}" height="{row_height}" fill="{row_fill}" fill-opacity="{row_opacity}"/>',
            f'<line x1="{SIDE_PADDING}" y1="{y + row_height}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{y + row_height}" stroke="#C0CAF5" stroke-opacity="0.075"/>',
            f'<rect x="82" y="{y + 8}" width="32" height="26" rx="8" fill="{podium_color or SURFACE_MUTED}" fill-opacity="{1 if podium_color else 0.72}" stroke="#C0CAF5" stroke-opacity="0.08"/>',
            f'<text x="98" y="{y + 26}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="900" fill="{TEXT_PRIMARY}">{rank}</text>',
            f'<rect x="142" y="{y + 7}" width="28" height="28" rx="9" fill="{level_color}" fill-opacity="0.10" stroke="{level_color}" stroke-opacity="0.28"/>',
            f'<text x="156" y="{y + 26}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="11" font-weight="900" fill="{level_color}">{level_mark}</text>',
            f'<text x="182" y="{y + 27}" font-family="Noto Sans CJK SC, sans-serif" font-size="14" font-weight="850" fill="{TEXT_PRIMARY}">{escape(team_name)}</text>',
            f'<text x="506" y="{y + 27}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="800" fill="{level_color}">{escape(level)}</text>',
            f'<rect x="590" y="{y + 7}" width="120" height="28" rx="9" fill="#2587BD" fill-opacity="0.10"/>',
            f'<text x="650" y="{y + 26}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="850" fill="#75BCE3">{escape(_format_points(row.base_points))}</text>',
            f'<rect x="730" y="{y + 7}" width="120" height="28" rx="9" fill="{ACCENT_PRIMARY}" fill-opacity="0.12"/>',
            f'<text x="790" y="{y + 26}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="14" font-weight="950" fill="{ACCENT_PRIMARY}">{escape(_format_points(row.total_points))}</text>',
            f'<text x="910" y="{y + 27}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="800" fill="{TEXT_SECONDARY}">{int(row.matches or 0)}</text>',
            f'<text x="1040" y="{y + 27}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="800" fill="{TEXT_SECONDARY}">{int(row.wins or 0)} / {int(row.draws or 0)} / {int(row.losses or 0)}</text>',
        ])
    _footer(parts, height, "HEIGO")
    return "".join(parts)


PLAYER_METRICS = {
    "goals": ("射手榜", "进球", "GOALS", WARNING),
    "assists": ("助攻榜", "助攻", "ASSISTS", ACCENT_PRIMARY),
    "mvps": ("最佳球员榜", "最佳", "MVP", ACCENT_SECONDARY),
}


def _player_ranking_rows(player_rankings: PlayerRankingsResponse, level: str, metric: str) -> list[Any]:
    normalized_metric = metric if metric in PLAYER_METRICS else "goals"
    rows = [row for row in player_rankings.rows if row.level == level and int(getattr(row, normalized_metric, 0) or 0) > 0]
    rows.sort(key=lambda row: (
        -int(getattr(row, normalized_metric, 0) or 0),
        -int(row.goals or 0),
        -int(row.assists or 0),
        -int(row.mvps or 0),
        str(row.player_name or ""),
    ))
    return rows


def _build_player_rankings_svg(player_rankings: PlayerRankingsResponse, level: str, metric: str = "goals") -> str:
    normalized_metric = metric if metric in PLAYER_METRICS else "goals"
    title_label, metric_label, metric_english, metric_color = PLAYER_METRICS[normalized_metric]
    rows = _player_ranking_rows(player_rankings, level, normalized_metric)
    coverage = next((item for item in player_rankings.coverage if item.level == level), None)
    row_height = 50
    table_y = 302
    table_header_height = 46
    content_rows = max(1, len(rows))
    height = max(820, table_y + table_header_height + content_rows * row_height + 98)
    played = int(coverage.played_matches or 0) if coverage else 0
    recorded = int(coverage.matches_with_events or 0) if coverage else 0
    missing = int(coverage.matches_missing_events or 0) if coverage else 0
    subtitle = f"球员比赛数据按主站实时明细汇总 · 已赛 {played} 场 · 已录明细 {recorded} 场"
    parts = _base_svg_parts(
        height,
        eyebrow="HEIGO PLAYER PERFORMANCE",
        title=f"{level}{title_label}",
        subtitle=subtitle,
        level=level,
        status_label=f"按{metric_label}排序 · {len(rows)} 人上榜",
    )
    tabs = (
        ("goals", "射手榜", sum(1 for row in player_rankings.rows if row.level == level and int(row.goals or 0) > 0)),
        ("assists", "助攻榜", sum(1 for row in player_rankings.rows if row.level == level and int(row.assists or 0) > 0)),
        ("mvps", "最佳球员榜", sum(1 for row in player_rankings.rows if row.level == level and int(row.mvps or 0) > 0)),
    )
    tab_width = 132
    for index, (key, label, count) in enumerate(tabs):
        x = SIDE_PADDING + index * (tab_width + 8)
        active = key == normalized_metric
        fill = "url(#siteAccent)" if active else SURFACE_MUTED
        fill_opacity = "1" if active else "0.70"
        text_color = BG_TOP if active else TEXT_SECONDARY
        parts.extend([
            f'<rect x="{x}" y="214" width="{tab_width}" height="46" rx="23" fill="{fill}" fill-opacity="{fill_opacity}" stroke="#C0CAF5" stroke-opacity="{0 if active else 0.10}"/>',
            f'<text x="{x + 20}" y="242" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="900" fill="{text_color}">{escape(label)}</text>',
            f'<rect x="{x + 96}" y="225" width="24" height="24" rx="12" fill="{BG_TOP if active else SURFACE_STRONG}" fill-opacity="{0.16 if active else 0.72}"/>',
            f'<text x="{x + 108}" y="242" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="10" font-weight="900" fill="{text_color}">{count}</text>',
        ])
    coverage_x = 500
    coverage_width = IMAGE_WIDTH - SIDE_PADDING - coverage_x
    parts.extend([
        f'<rect x="{coverage_x}" y="210" width="{coverage_width}" height="58" rx="14" fill="{SURFACE_MUTED}" fill-opacity="0.70" stroke="#C0CAF5" stroke-opacity="0.10"/>',
    ])
    coverage_items = (("已赛", played, TEXT_PRIMARY), ("已录明细", recorded, SUCCESS), ("待补", missing, DANGER if missing else SUCCESS))
    item_width = 104
    for index, (label, value, color) in enumerate(coverage_items):
        x = coverage_x + 16 + index * item_width
        parts.extend([
            f'<text x="{x}" y="231" font-family="Noto Sans CJK SC, sans-serif" font-size="9" font-weight="750" fill="{TEXT_SECONDARY}">{escape(label)}</text>',
            f'<text x="{x}" y="254" font-family="DejaVu Sans, sans-serif" font-size="19" font-weight="950" fill="{color}">{value}</text>',
        ])
    note = f"还有 {missing} 场待补球员明细" if missing else ("已赛比赛均已录入球员明细" if played else "暂无已赛比赛")
    parts.append(f'<text x="{IMAGE_WIDTH - SIDE_PADDING - 16}" y="244" text-anchor="end" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="700" fill="{TEXT_SECONDARY}">{escape(note)}</text>')
    table_height = table_header_height + content_rows * row_height
    parts.extend([
        f'<rect x="{SIDE_PADDING}" y="{table_y}" width="{CONTENT_WIDTH}" height="{table_height}" rx="16" fill="{SURFACE_STRONG}" fill-opacity="0.74" stroke="#C0CAF5" stroke-opacity="0.11"/>',
        f'<path d="M{SIDE_PADDING + 16} {table_y}H{IMAGE_WIDTH - SIDE_PADDING - 16}Q{IMAGE_WIDTH - SIDE_PADDING} {table_y} {IMAGE_WIDTH - SIDE_PADDING} {table_y + 16}V{table_y + table_header_height}H{SIDE_PADDING}V{table_y + 16}Q{SIDE_PADDING} {table_y} {SIDE_PADDING + 16} {table_y}Z" fill="{ACCENT_PRIMARY}" fill-opacity="0.12"/>',
    ])
    headers = (
        ("排名", 98, "middle"), ("球员", 142, "start"), ("球队", 520, "start"),
        ("进球", 808, "middle"), ("助攻", 890, "middle"), ("最佳", 972, "middle"),
        ("出场", 1066, "middle"),
    )
    for label, x, anchor in headers:
        parts.append(f'<text x="{x}" y="{table_y + 29}" text-anchor="{anchor}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="850" fill="{TEXT_PRIMARY}">{label}</text>')
    if not rows:
        parts.extend([
            f'<text x="{IMAGE_WIDTH / 2}" y="{table_y + 78}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="17" font-weight="900" fill="{TEXT_PRIMARY}">当前没有{metric_label}记录</text>',
            f'<text x="{IMAGE_WIDTH / 2}" y="{table_y + 105}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="11" font-weight="650" fill="{TEXT_SECONDARY}">比赛明细录入后，榜单会与主站同步更新</text>',
        ])
    for index, row in enumerate(rows):
        y = table_y + table_header_height + index * row_height
        rank = index + 1
        row_fill = metric_color if rank <= 3 else SURFACE_MUTED
        row_opacity = 0.07 if rank <= 3 else (0.28 if index % 2 else 0.14)
        player_name = _truncate_text(row.player_name, 31)
        team_name = _truncate_text(common_chinese_team_name(row.team_name), 23)
        values = {"goals": int(row.goals or 0), "assists": int(row.assists or 0), "mvps": int(row.mvps or 0)}
        parts.extend([
            f'<rect x="{SIDE_PADDING}" y="{y}" width="{CONTENT_WIDTH}" height="{row_height}" fill="{row_fill}" fill-opacity="{row_opacity}"/>',
            f'<line x1="{SIDE_PADDING}" y1="{y + row_height}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{y + row_height}" stroke="#C0CAF5" stroke-opacity="0.075"/>',
            f'<text x="98" y="{y + 32}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="15" font-weight="900" fill="{metric_color if rank <= 3 else TEXT_SECONDARY}">{rank}</text>',
            f'<text x="142" y="{y + 32}" font-family="DejaVu Sans, Noto Sans CJK SC, sans-serif" font-size="15" font-weight="850" fill="{TEXT_PRIMARY}">{escape(player_name)}</text>',
            f'<text x="520" y="{y + 31}" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="700" fill="{TEXT_SECONDARY}">{escape(team_name)}</text>',
        ])
        for key, x in (("goals", 808), ("assists", 890), ("mvps", 972)):
            color = metric_color if key == normalized_metric else TEXT_SECONDARY
            weight = 950 if key == normalized_metric else 750
            parts.append(f'<text x="{x}" y="{y + 32}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="{17 if key == normalized_metric else 14}" font-weight="{weight}" fill="{color}">{values[key]}</text>')
        parts.append(f'<text x="1066" y="{y + 31}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" font-weight="750" fill="{TEXT_SECONDARY}">{int(row.appearances or 0)}</text>')
    _footer(parts, height, level)
    return "".join(parts)


def _payload_fingerprint(kind: str, level: str, payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        raw = payload.model_dump(mode="json")
    else:
        raw = payload
    encoded = json.dumps(raw, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return md5(f"{kind}:{level}:{encoded}".encode("utf-8")).hexdigest()


def render_league_report_png(
    kind: str,
    level: str,
    payload: StandingsResponse | SuspensionsResponse,
    cache_root: str | Path,
) -> RenderedLeagueReportPng:
    normalized_kind = "suspensions" if kind == "suspensions" else "standings"
    fingerprint = _payload_fingerprint(normalized_kind, level, payload)
    cache_key = f"league_{normalized_kind}_{level}_{fingerprint[:20]}_tpl{TEMPLATE_VERSION}"
    etag = md5(cache_key.encode("utf-8")).hexdigest()
    target = Path(cache_root) / "league-report" / f"{cache_key}.png"
    if target.exists():
        return RenderedLeagueReportPng(str(target), target.name, etag, "HIT")
    if cairosvg is None:
        raise RuntimeError("cairosvg_not_installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    svg = _build_suspensions_svg(payload, level) if normalized_kind == "suspensions" else _build_standings_svg(payload, level)
    target.write_bytes(cairosvg.svg2png(bytestring=svg.encode("utf-8")))
    return RenderedLeagueReportPng(str(target), target.name, etag, "MISS")


def render_statistics_report_png(
    kind: str,
    payload: RankingsResponse | PlayerRankingsResponse,
    cache_root: str | Path,
    *,
    level: str | None = None,
    metric: str = "goals",
) -> RenderedLeagueReportPng:
    normalized_kind = "player_rankings" if kind == "player_rankings" else "rankings"
    normalized_level = level if normalized_kind == "player_rankings" and level in LEVEL_COLORS else "HEIGO"
    normalized_metric = metric if metric in PLAYER_METRICS else "goals"
    fingerprint = _payload_fingerprint(normalized_kind, f"{normalized_level}:{normalized_metric}", payload)
    cache_key = f"statistics_{normalized_kind}_{normalized_level}_{normalized_metric}_{fingerprint[:20]}_tpl{TEMPLATE_VERSION}"
    etag = md5(cache_key.encode("utf-8")).hexdigest()
    target = Path(cache_root) / "statistics-report" / f"{cache_key}.png"
    if target.exists():
        return RenderedLeagueReportPng(str(target), target.name, etag, "HIT")
    if cairosvg is None:
        raise RuntimeError("cairosvg_not_installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    if normalized_kind == "player_rankings":
        svg = _build_player_rankings_svg(payload, normalized_level, normalized_metric)
    else:
        svg = _build_rankings_svg(payload)
    target.write_bytes(cairosvg.svg2png(bytestring=svg.encode("utf-8")))
    return RenderedLeagueReportPng(str(target), target.name, etag, "MISS")
