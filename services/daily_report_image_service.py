from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from html import escape
from pathlib import Path
import re

try:
    import cairosvg
except ImportError:  # pragma: no cover - runtime dependency
    cairosvg = None

from schemas_read import DailyReportResponse
from services.team_name_service import COMMON_CHINESE_TEAM_NAMES


IMAGE_WIDTH = 1200
SIDE_PADDING = 64
CONTENT_WIDTH = IMAGE_WIDTH - SIDE_PADDING * 2
TEMPLATE_VERSION = 6

SCORE_PATTERN = re.compile(r"(?<!\d)\d{1,2}:\d{1,2}(?!\d)")
ITEM_PATTERN = re.compile(
    r"^(?:【(?P<tags>[^】]+)】)?(?P<competition>[^｜：]+)｜(?P<matchup>[^：]+)：(?P<body>.+)$"
)
PLAYER_ACTION_PATTERN = re.compile(
    r"(?:^|[。；！!?，：])\s*"
    r"(?P<name>(?:[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*"
    r"(?:\s+[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*){0,5}|"
    r"[\u3400-\u9fff·]{2,12}))"
    r"(?=\s*(?:独中三元|上演帽子戏法|帽子戏法|梅开二度|送出\s*\d+\s*次助攻|"
    r"贡献\s*\d+\s*球|当选本场最佳))"
)
SUSPENSION_PLAYER_PATTERN = re.compile(
    r"^\s*(?P<name>(?:[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*"
    r"(?:\s+[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*){0,5}|"
    r"[\u3400-\u9fff·]{2,12}))(?=（[^）]*(?:黄|红牌|伤停))"
)
KNOWN_TEAM_NAMES = tuple(sorted(set(COMMON_CHINESE_TEAM_NAMES.values()), key=len, reverse=True))


@dataclass(frozen=True)
class RenderedDailyReportPng:
    file_path: str
    file_name: str
    etag: str
    cache_status: str


@dataclass(frozen=True)
class _StyledSpan:
    text: str
    kind: str = "plain"


@dataclass(frozen=True)
class _PreparedItem:
    tags: tuple[str, ...]
    competition: str
    matchup_lines: tuple[tuple[_StyledSpan, ...], ...]
    result_line: tuple[_StyledSpan, ...]
    body_lines: tuple[tuple[_StyledSpan, ...], ...]


def _text_units(value: str) -> int:
    return sum(1 if ord(char) < 128 else 2 for char in value)


def _entity_ranges(value: str, extra_teams: tuple[str, ...] = ()) -> list[tuple[int, int, str, int]]:
    ranges: list[tuple[int, int, str, int]] = []
    for match in SCORE_PATTERN.finditer(value):
        ranges.append((match.start(), match.end(), "score", 30))
    for team_name in tuple(dict.fromkeys((*extra_teams, *KNOWN_TEAM_NAMES))):
        if not team_name:
            continue
        for match in re.finditer(re.escape(team_name), value, flags=re.IGNORECASE):
            ranges.append((match.start(), match.end(), "team", 10))
    for pattern in (PLAYER_ACTION_PATTERN, SUSPENSION_PLAYER_PATTERN):
        for match in pattern.finditer(value):
            ranges.append((match.start("name"), match.end("name"), "player", 20))
    return ranges


def _styled_segments(value: str, extra_teams: tuple[str, ...] = ()) -> list[_StyledSpan]:
    text = str(value or "")
    if not text:
        return []
    styles: list[tuple[str, int]] = [("plain", 0) for _ in text]
    for start, end, kind, priority in _entity_ranges(text, extra_teams):
        for index in range(max(0, start), min(len(text), end)):
            if priority >= styles[index][1]:
                styles[index] = (kind, priority)
    result: list[_StyledSpan] = []
    start = 0
    active_kind = styles[0][0]
    for index in range(1, len(text)):
        kind = styles[index][0]
        if kind == active_kind:
            continue
        result.append(_StyledSpan(text[start:index], active_kind))
        start = index
        active_kind = kind
    result.append(_StyledSpan(text[start:], active_kind))
    return result


def _append_span(line: list[_StyledSpan], text: str, kind: str) -> None:
    if not text:
        return
    if line and line[-1].kind == kind:
        line[-1] = _StyledSpan(line[-1].text + text, kind)
    else:
        line.append(_StyledSpan(text, kind))


def _wrap_styled_text(
    value: str,
    max_units: int,
    *,
    extra_teams: tuple[str, ...] = (),
) -> list[list[_StyledSpan]]:
    segments = _styled_segments(value, extra_teams)
    if not segments:
        return []
    lines: list[list[_StyledSpan]] = []
    current: list[_StyledSpan] = []
    current_units = 0
    for segment in segments:
        segment_units = _text_units(segment.text)
        if segment.kind != "plain" and current and segment_units <= max_units and current_units + segment_units > max_units:
            lines.append(current)
            current = []
            current_units = 0
        for char in segment.text:
            char_units = 1 if ord(char) < 128 else 2
            if current and current_units + char_units > max_units:
                lines.append(current)
                current = []
                current_units = 0
            _append_span(current, char, segment.kind)
            current_units += char_units
    if current:
        lines.append(current)
    return lines


def _matchup_teams(value: str) -> tuple[str, ...]:
    parts = re.split(r"\s+(?:vs|VS|对)\s+", str(value or "").strip())
    return tuple(part.strip() for part in parts if part.strip())


def _split_result_and_commentary(value: str) -> tuple[str, str]:
    body = str(value or "").strip()
    first_sentence, separator, remainder = body.partition("。")
    if separator and SCORE_PATTERN.search(first_sentence):
        return first_sentence.strip(), remainder.strip()
    if SCORE_PATTERN.search(body):
        return body, ""
    return "", body


def _prepare_item(value: str, *, focus_only: bool) -> _PreparedItem:
    raw = str(value or "").strip()
    match = ITEM_PATTERN.match(raw)
    if match:
        tags = tuple(tag.strip() for tag in str(match.group("tags") or "").split("·") if tag.strip())
        competition = str(match.group("competition") or "").strip()
        matchup = str(match.group("matchup") or "").strip()
        body = str(match.group("body") or "").strip()
    else:
        tag_match = re.match(r"^【(?P<tags>[^】]+)】(?P<body>.*)$", raw)
        tags = tuple(tag.strip() for tag in str(tag_match.group("tags") if tag_match else "").split("·") if tag.strip())
        competition = ""
        matchup = ""
        body = str(tag_match.group("body") if tag_match else raw).strip()
    teams = _matchup_teams(matchup)
    result_text, commentary = _split_result_and_commentary(body)
    matchup_units = 78 if focus_only else 104
    body_units = 92 if focus_only else 118
    return _PreparedItem(
        tags=tags,
        competition=competition,
        matchup_lines=tuple(tuple(line) for line in _wrap_styled_text(matchup, matchup_units, extra_teams=teams)),
        result_line=tuple(_styled_segments(result_text, extra_teams=teams)),
        body_lines=tuple(tuple(line) for line in _wrap_styled_text(commentary, body_units, extra_teams=teams)),
    )


def _styled_units(spans: tuple[_StyledSpan, ...] | list[_StyledSpan]) -> int:
    return sum(_text_units(span.text) for span in spans)


def _fit_single_line_font(
    spans: tuple[_StyledSpan, ...] | list[_StyledSpan],
    *,
    preferred_size: int,
    minimum_size: int,
    available_width: float,
) -> int:
    units = max(1, _styled_units(spans))
    estimated_width = units * preferred_size * 0.52
    if estimated_width <= available_width:
        return preferred_size
    return max(minimum_size, int(available_width / (units * 0.52)))


def _rich_text(
    spans: tuple[_StyledSpan, ...] | list[_StyledSpan],
    *,
    x: float,
    y: float,
    font_size: int,
    fill: str,
    weight: int,
    role: str = "",
) -> str:
    role_attr = f' data-role="{escape(role)}"' if role else ""
    parts = [
        f'<text{role_attr} x="{x:.1f}" y="{y:.1f}" font-family="Noto Sans CJK SC, sans-serif" '
        f'font-size="{font_size}" font-weight="{weight}" fill="{fill}">'
    ]
    for span in spans:
        attrs = ""
        if span.kind == "score":
            attrs = (
                f' data-kind="score" fill="#FFC857" font-family="DejaVu Sans, sans-serif" '
                f'font-size="{font_size + 3}" font-weight="950"'
            )
        elif span.kind == "team":
            attrs = ' data-kind="team" fill="#F8FBFF" font-weight="950"'
        elif span.kind == "player":
            attrs = ' data-kind="player" fill="#55D99A" font-weight="950"'
        parts.append(f'<tspan{attrs}>{escape(span.text)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def _item_height(item: _PreparedItem, *, focus_only: bool) -> int:
    matchup_line_height = 34 if focus_only else 30
    body_line_height = 35 if focus_only else 30
    result_line_height = 31 if focus_only else 27
    meta_height = 48 if item.competition or item.tags else 0
    matchup_height = len(item.matchup_lines) * matchup_line_height
    result_height = result_line_height if item.result_line else 0
    body_height = len(item.body_lines) * body_line_height
    gaps = 0
    if matchup_height and (result_height or body_height):
        gaps += 10
    if result_height and body_height:
        gaps += 8
    return 42 + meta_height + matchup_height + result_height + gaps + body_height


def _parse_sections(content: str) -> tuple[str, list[tuple[str, list[str]]]]:
    overview = "今日暂无新增赛果。"
    sections: list[tuple[str, list[str]]] = []
    active_title = ""
    active_lines: list[str] = []
    for raw_line in str(content or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("【") and line.endswith("】"):
            if active_title and active_lines:
                sections.append((active_title, active_lines))
            active_title = line[1:-1]
            active_lines = []
        elif active_title:
            active_lines.append(line)
        elif overview == "今日暂无新增赛果。":
            overview = line
    if active_title and active_lines:
        sections.append((active_title, active_lines))
    return overview, sections


def _section_color(title: str) -> str:
    if title == "焦点头版":
        return "#F4B740"
    if title == "常规战报":
        return "#2ED084"
    if title == "伤停动态":
        return "#E65B65"
    return "#66A8FF"


def _build_svg(report: DailyReportResponse, *, scope: str = "full") -> str:
    focus_only = scope == "focus"
    source_content = report.focus_content if focus_only else report.content
    overview, sections = _parse_sections(source_content)
    body_font_size = 20 if focus_only else 17
    body_line_height = 35 if focus_only else 30
    result_font_size = 20 if focus_only else 17
    result_line_height = 31 if focus_only else 27
    matchup_font_size = 25 if focus_only else 21
    matchup_line_height = 34 if focus_only else 30
    prepared: list[tuple[str, list[_PreparedItem]]] = []
    content_height = 0
    for title, items in sections:
        prepared_items = [_prepare_item(item, focus_only=focus_only) for item in items]
        prepared.append((title, prepared_items))
        content_height += 72
        content_height += sum(_item_height(item, focus_only=focus_only) + 14 for item in prepared_items)
    height = max(820, 334 + content_height + 92)
    eyebrow = "HEIGO / DAILY MATCH INTELLIGENCE"
    title_parts = [part.strip() for part in str(report.title or "HEIGO 联赛日报").split("｜", 1)]
    display_title = title_parts[0].replace("HEIGO", "").strip() or "联赛日报"
    if focus_only:
        display_title = display_title.replace("联赛日报", "焦点头版")
    date_label = title_parts[1] if len(title_parts) > 1 else report.report_date

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{IMAGE_WIDTH}" height="{height}" viewBox="0 0 {IMAGE_WIDTH} {height}">',
        '<defs>',
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#091321"/><stop offset="0.58" stop-color="#101D30"/><stop offset="1" stop-color="#13263A"/></linearGradient>',
        '<linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#17253A"/><stop offset="1" stop-color="#1C2B40"/></linearGradient>',
        '<linearGradient id="scoreRail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFC857"/><stop offset="1" stop-color="#2ED084"/></linearGradient>',
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#050A12" flood-opacity="0.28"/></filter>',
        '</defs>',
        f'<rect width="{IMAGE_WIDTH}" height="{height}" fill="url(#bg)"/>',
        '<path d="M860 0H1200V258C1122 238 1047 191 1000 131C955 74 916 31 860 0Z" fill="#2ED084" opacity="0.055"/>',
        '<circle cx="1128" cy="74" r="168" fill="none" stroke="#7DB7FF" stroke-width="2" opacity="0.10"/>',
        '<circle cx="1128" cy="74" r="88" fill="none" stroke="#2ED084" stroke-width="2" opacity="0.11"/>',
        '<line x1="1038" y1="0" x2="1038" y2="190" stroke="#FFFFFF" stroke-opacity="0.06"/>',
        f'<text x="{SIDE_PADDING}" y="60" font-family="DejaVu Sans, sans-serif" font-size="15" font-weight="900" letter-spacing="3.4" fill="#2ED084">{eyebrow}</text>',
        f'<text x="{SIDE_PADDING}" y="124" font-family="Noto Sans CJK SC, sans-serif" font-size="48" font-weight="950" letter-spacing="-1" fill="#F7FAFD">{escape(display_title)}</text>',
        f'<text x="{IMAGE_WIDTH - SIDE_PADDING}" y="117" text-anchor="end" font-family="Noto Sans CJK SC, sans-serif" font-size="34" font-weight="900" fill="#FFC857">{escape(date_label)}</text>',
        f'<text x="{SIDE_PADDING}" y="168" font-family="Noto Sans CJK SC, sans-serif" font-size="19" font-weight="600" fill="#9FB0C4">{escape(overview)}</text>',
        f'<rect x="{SIDE_PADDING}" y="202" width="{CONTENT_WIDTH}" height="92" rx="18" fill="#F4F7FA" filter="url(#shadow)"/>',
        f'<rect x="{SIDE_PADDING}" y="202" width="{CONTENT_WIDTH}" height="5" rx="2.5" fill="url(#scoreRail)"/>',
    ]
    stats = (
        ("比赛", report.match_count, "MATCHES"),
        ("进球", report.goal_count, "GOALS"),
        ("对阵", report.fixture_group_count, "FIXTURES"),
        ("焦点", report.focus_count, "FRONT PAGE"),
    )
    if not focus_only:
        stats += (("伤停", report.suspension_count, "INJURIES"),)
    stat_width = CONTENT_WIDTH / len(stats)
    for index, (label, value, english) in enumerate(stats):
        x = SIDE_PADDING + stat_width * index
        if index:
            parts.append(f'<line x1="{x:.1f}" y1="226" x2="{x:.1f}" y2="278" stroke="#DCE3EA"/>')
        parts.extend([
            f'<text x="{x + 24:.1f}" y="239" font-family="Noto Sans CJK SC, sans-serif" font-size="10" font-weight="900" letter-spacing="1.4" fill="#78879A">{english} / {label}</text>',
            f'<text x="{x + 24:.1f}" y="274" font-family="DejaVu Sans, sans-serif" font-size="30" font-weight="950" fill="#0C1726">{int(value)}</text>',
        ])

    y = 332
    for section_index, (title, prepared_items) in enumerate(prepared, start=1):
        accent = _section_color(title)
        parts.extend([
            f'<text x="{SIDE_PADDING}" y="{y + 28}" font-family="DejaVu Sans, sans-serif" font-size="12" font-weight="950" letter-spacing="2" fill="{accent}">SECTION {section_index:02d}</text>',
            f'<text x="{SIDE_PADDING + 122}" y="{y + 31}" font-family="Noto Sans CJK SC, sans-serif" font-size="24" font-weight="950" fill="#F4F7FA">{escape(title)}</text>',
            f'<line x1="{SIDE_PADDING + 255}" y1="{y + 24}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{y + 24}" stroke="{accent}" stroke-opacity="0.30"/>',
        ])
        y += 58
        for item_index, item in enumerate(prepared_items):
            item_height = _item_height(item, focus_only=focus_only)
            parts.extend([
                f'<rect x="{SIDE_PADDING}" y="{y}" width="{CONTENT_WIDTH}" height="{item_height}" rx="18" fill="url(#card)" stroke="#FFFFFF" stroke-opacity="0.075"/>',
                f'<rect x="{SIDE_PADDING}" y="{y}" width="5" height="{item_height}" rx="2.5" fill="{accent}"/>',
                f'<rect x="{SIDE_PADDING + 20}" y="{y + 20}" width="38" height="27" rx="8" fill="{accent}" fill-opacity="0.13" stroke="{accent}" stroke-opacity="0.34"/>',
                f'<text x="{SIDE_PADDING + 39}" y="{y + 39}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="12" font-weight="950" fill="{accent}">{item_index + 1:02d}</text>',
            ])
            content_x = SIDE_PADDING + 78
            cursor_y = y + 40
            if item.competition or item.tags:
                if item.competition:
                    competition_width = max(76, 26 + _text_units(item.competition) * 6.5)
                    parts.extend([
                        f'<rect x="{content_x}" y="{y + 19}" width="{competition_width:.1f}" height="28" rx="8" fill="#FFFFFF" fill-opacity="0.07"/>',
                        f'<text x="{content_x + 13:.1f}" y="{y + 38}" font-family="Noto Sans CJK SC, sans-serif" font-size="13" font-weight="900" fill="#B8C6D8">{escape(item.competition)}</text>',
                    ])
                    tag_x = content_x + competition_width + 10
                else:
                    tag_x = content_x
                for tag in item.tags[:3]:
                    tag_width = 28 + _text_units(tag) * 6.2
                    parts.extend([
                        f'<rect x="{tag_x:.1f}" y="{y + 19}" width="{tag_width:.1f}" height="28" rx="14" fill="{accent}" fill-opacity="0.10" stroke="{accent}" stroke-opacity="0.32"/>',
                        f'<text x="{tag_x + tag_width / 2:.1f}" y="{y + 38}" text-anchor="middle" font-family="Noto Sans CJK SC, sans-serif" font-size="12" font-weight="900" fill="{accent}">{escape(tag)}</text>',
                    ])
                    tag_x += tag_width + 8
                cursor_y = y + 88
            for line in item.matchup_lines:
                parts.append(_rich_text(
                    line,
                    x=content_x,
                    y=cursor_y,
                    font_size=matchup_font_size,
                    fill="#F5F8FC",
                    weight=850,
                ))
                cursor_y += matchup_line_height
            if item.matchup_lines and (item.result_line or item.body_lines):
                cursor_y += 10
            if item.result_line:
                fitted_result_font = _fit_single_line_font(
                    item.result_line,
                    preferred_size=result_font_size,
                    minimum_size=14 if focus_only else 12,
                    available_width=CONTENT_WIDTH - 88,
                )
                parts.append(_rich_text(
                    item.result_line,
                    x=content_x,
                    y=cursor_y,
                    font_size=fitted_result_font,
                    fill="#D8E1EC",
                    weight=720,
                    role="scoreline",
                ))
                cursor_y += result_line_height
                if item.body_lines:
                    cursor_y += 8
            for line in item.body_lines:
                parts.append(_rich_text(
                    line,
                    x=content_x,
                    y=cursor_y,
                    font_size=body_font_size,
                    fill="#C7D2DF",
                    weight=620,
                ))
                cursor_y += body_line_height
            y += item_height + 12
        y += 8

    parts.extend([
        f'<line x1="{SIDE_PADDING}" y1="{height - 64}" x2="{IMAGE_WIDTH - SIDE_PADDING}" y2="{height - 64}" stroke="#FFFFFF" stroke-opacity="0.10"/>',
        f'<text x="{SIDE_PADDING}" y="{height - 28}" font-family="Noto Sans CJK SC, sans-serif" font-size="13" font-weight="700" letter-spacing="1" fill="#78879A">HEIGO 联机联赛数据库 · 数据以主站实时记录为准</text>',
        f'<text x="{IMAGE_WIDTH - SIDE_PADDING}" y="{height - 28}" text-anchor="end" font-family="Noto Sans CJK SC, sans-serif" font-size="13" fill="#78879A">{escape(report.report_date)}</text>',
        '</svg>',
    ])
    return "".join(parts)


def render_daily_report_png(
    report: DailyReportResponse,
    cache_root: str | Path,
    *,
    scope: str = "full",
) -> RenderedDailyReportPng:
    normalized_scope = "focus" if scope == "focus" else "full"
    source_content = report.focus_content if normalized_scope == "focus" else report.content
    fingerprint = str(report.fingerprint or md5(source_content.encode("utf-8")).hexdigest())
    cache_key = f"daily_{normalized_scope}_{report.report_date}_{fingerprint[:20]}_tpl{TEMPLATE_VERSION}"
    etag = md5(cache_key.encode("utf-8")).hexdigest()
    target = Path(cache_root) / "daily-report" / f"{cache_key}.png"
    if target.exists():
        return RenderedDailyReportPng(str(target), target.name, etag, "HIT")
    if cairosvg is None:
        raise RuntimeError("cairosvg_not_installed")
    target.parent.mkdir(parents=True, exist_ok=True)
    png_bytes = cairosvg.svg2png(bytestring=_build_svg(report, scope=normalized_scope).encode("utf-8"))
    target.write_bytes(png_bytes)
    return RenderedDailyReportPng(str(target), target.name, etag, "MISS")
