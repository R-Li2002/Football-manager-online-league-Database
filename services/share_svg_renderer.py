from __future__ import annotations

from html import escape
from math import cos, pi, sin

from schemas_read import PlayerAttributeDetailResponse, PlayerResponse, TeamInfoResponse, WageDetailResponse
from services.share_card_model_service import (
    RosterPlayerRow,
    RosterShareCardModel,
    SHARE_FONT_FAMILY,
    ShareChip,
    ShareGroup,
    ShareMetric,
    WageShareCardModel,
    build_player_share_card_model,
    build_roster_share_card_model,
    build_wage_share_card_model,
)


def _theme_tokens(theme: str) -> dict[str, str]:
    if theme == "light":
        return {
            "bg": "#eef4fb",
            "bg_2": "#f7fbff",
            "panel": "rgba(255,255,255,0.96)",
            "panel_soft": "rgba(247,250,253,0.98)",
            "line": "rgba(100,116,139,0.16)",
            "text": "#172033",
            "muted": "#5f6c84",
            "accent": "#2563eb",
            "accent_2": "#16a34a",
            "accent_soft": "rgba(37,99,235,0.10)",
        }
    return {
        "bg": "#0b1220",
        "bg_2": "#111b30",
        "panel": "rgba(15,23,42,0.92)",
        "panel_soft": "rgba(30,41,59,0.82)",
        "line": "rgba(148,163,184,0.18)",
        "text": "#ecf3ff",
        "muted": "#94a3b8",
        "accent": "#38bdf8",
        "accent_2": "#22c55e",
        "accent_soft": "rgba(56,189,248,0.14)",
    }


def _radar_polygon_points(metrics: tuple[ShareMetric, ...], *, center_x: float, center_y: float, radius: float) -> str:
    points: list[str] = []
    count = len(metrics)
    for index, item in enumerate(metrics):
        angle = (-pi / 2) + (2 * pi * index / count)
        scale = item.value / 20.0
        x = center_x + cos(angle) * radius * scale
        y = center_y + sin(angle) * radius * scale
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _radar_axis_points(count: int, *, center_x: float, center_y: float, radius: float) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(count):
        angle = (-pi / 2) + (2 * pi * index / count)
        x = center_x + cos(angle) * radius
        y = center_y + sin(angle) * radius
        points.append((x, y))
    return points


def _render_svg_group(
    group: ShareGroup,
    *,
    x: int,
    y: int,
    width: int,
    text_fill: str,
    muted_fill: str,
    line_fill: str,
    bar_fill: str,
) -> str:
    row_y = y + 44
    rows: list[str] = [
        f'<text x="{x + 18}" y="{y + 28}" font-size="14" font-weight="700" fill="{muted_fill}" letter-spacing="1.5">{escape(group.title)}</text>'
    ]
    for item in group.items:
        rows.append(
            f'<text x="{x + 18}" y="{row_y}" font-size="13" fill="{text_fill}">{escape(item.label)}</text>'
            f'<text x="{x + 120}" y="{row_y}" font-size="13" font-weight="700" fill="{text_fill}" text-anchor="end">{int(round(item.value))}</text>'
            f'<rect x="{x + 134}" y="{row_y - 10}" width="{width - 152}" height="10" rx="5" fill="{line_fill}" />'
            f'<rect x="{x + 134}" y="{row_y - 10}" width="{((width - 152) * item.percent / 100):.1f}" height="10" rx="5" fill="{bar_fill}" />'
        )
        row_y += 28
    return "".join(rows)


def build_player_share_svg(
    player: PlayerAttributeDetailResponse,
    *,
    version: str | None = None,
    step: int = 0,
    theme: str = "dark",
) -> str:
    model = build_player_share_card_model(player, version=version, step=step, theme=theme)
    tokens = _theme_tokens(model.theme)
    width = model.canvas_width
    height = model.canvas_height
    version_suffix = f" | {model.version_label}" if model.version_label else ""
    preview_suffix = f" | {model.weak_foot_label}" if model.weak_foot_label else ""

    info_rows = []
    info_y = 180
    for row in model.info_rows:
        info_rows.append(
            f'<text x="78" y="{info_y}" font-size="13" fill="{tokens["muted"]}">{escape(row.label)}</text>'
            f'<text x="378" y="{info_y}" font-size="15" font-weight="700" fill="{tokens["text"]}" text-anchor="end">{escape(row.value)}</text>'
            f'<line x1="78" y1="{info_y + 14}" x2="378" y2="{info_y + 14}" stroke="{tokens["line"]}" />'
        )
        info_y += 36

    position_chips = []
    chip_x = 78
    chip_y = 544
    for chip in model.position_chips or (ShareChip("NONE", "No data"),):
        chip_width = max(76, 22 + len(chip.label) * 9 + len(chip.value) * 7)
        position_chips.append(
            f'<rect x="{chip_x}" y="{chip_y}" width="{chip_width}" height="30" rx="15" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />'
            f'<text x="{chip_x + 16}" y="{chip_y + 20}" font-size="12" font-weight="700" fill="{tokens["text"]}">{escape(chip.label)}</text>'
            f'<text x="{chip_x + chip_width - 14}" y="{chip_y + 20}" font-size="12" fill="{tokens["muted"]}" text-anchor="end">{escape(chip.value)}</text>'
        )
        chip_x += chip_width + 10
        if chip_x > 330:
            chip_x = 78
            chip_y += 40

    top_position_chips = []
    top_chip_x = 78
    top_chip_y = chip_y + 72
    for chip in model.top_position_chips or (ShareChip("NONE", "No data"),):
        chip_width = max(92, 20 + len(chip.label) * 9 + len(chip.value) * 7)
        top_position_chips.append(
            f'<rect x="{top_chip_x}" y="{top_chip_y}" width="{chip_width}" height="30" rx="15" fill="{tokens["accent_soft"]}" stroke="{tokens["line"]}" />'
            f'<text x="{top_chip_x + 16}" y="{top_chip_y + 20}" font-size="12" font-weight="700" fill="{tokens["accent"]}">{escape(chip.label)}</text>'
            f'<text x="{top_chip_x + chip_width - 14}" y="{top_chip_y + 20}" font-size="12" fill="{tokens["text"]}" text-anchor="end">{escape(chip.value)}</text>'
        )
        top_chip_x += chip_width + 10
        if top_chip_x > 330:
            top_chip_x = 78
            top_chip_y += 40

    radar_center_x = 1180
    radar_center_y = 890
    radar_radius = 150
    axis_points = _radar_axis_points(len(model.radar_metrics), center_x=radar_center_x, center_y=radar_center_y, radius=radar_radius)
    grid_rings = []
    for scale in (0.25, 0.5, 0.75, 1.0):
        ring_points = []
        for point_x, point_y in axis_points:
            ring_points.append(f"{radar_center_x + (point_x - radar_center_x) * scale:.1f},{radar_center_y + (point_y - radar_center_y) * scale:.1f}")
        grid_rings.append(f'<polygon points="{" ".join(ring_points)}" fill="none" stroke="{tokens["line"]}" stroke-width="1" />')

    radar_axes = []
    radar_labels = []
    radar_rows = []
    for index, metric in enumerate(model.radar_metrics):
        point_x, point_y = axis_points[index]
        radar_axes.append(
            f'<line x1="{radar_center_x}" y1="{radar_center_y}" x2="{point_x:.1f}" y2="{point_y:.1f}" stroke="{tokens["line"]}" stroke-width="1" />'
        )
        label_x = radar_center_x + (point_x - radar_center_x) * 1.12
        label_y = radar_center_y + (point_y - radar_center_y) * 1.12
        radar_labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" font-size="12" fill="{tokens["muted"]}" text-anchor="middle">{escape(metric.label)}</text>'
        )
        radar_rows.append(
            f'<text x="1024" y="{748 + index * 24}" font-size="13" fill="{tokens["text"]}">{escape(metric.label)}</text>'
            f'<text x="1124" y="{748 + index * 24}" font-size="13" font-weight="700" fill="{tokens["text"]}" text-anchor="end">{metric.value:.1f}</text>'
        )

    radar_polygon = _radar_polygon_points(model.radar_metrics, center_x=radar_center_x, center_y=radar_center_y, radius=radar_radius)
    habits_block = ""
    if model.habit_text:
        block_y = min(height - 170, top_chip_y + 74)
        habits_block = (
            f'<rect x="60" y="{block_y}" width="360" height="110" rx="18" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />'
            f'<text x="78" y="{block_y + 28}" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">Player Traits</text>'
            f'<text x="78" y="{block_y + 60}" font-size="14" fill="{tokens["text"]}">{escape(model.habit_text)}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{tokens["bg"]}" />
      <stop offset="100%" stop-color="{tokens["bg_2"]}" />
    </linearGradient>
    <linearGradient id="bar-gradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{tokens["accent"]}" />
      <stop offset="100%" stop-color="{tokens["accent_2"]}" />
    </linearGradient>
    <style>
      text {{
        font-family: {SHARE_FONT_FAMILY};
      }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg-gradient)" />
  <rect x="30" y="28" width="{width - 60}" height="{height - 56}" rx="26" fill="{tokens["panel"]}" stroke="{tokens["line"]}" />
  <rect x="60" y="60" width="160" height="32" rx="16" fill="{tokens["accent_soft"]}" />
  <text x="140" y="81" font-size="12" font-weight="800" fill="{tokens["accent"]}" text-anchor="middle" letter-spacing="1.6">HEIGO PLAYER SHARE</text>
  <text x="{width - 66}" y="82" font-size="13" font-weight="700" fill="{tokens["muted"]}" text-anchor="end">{escape(model.preview_label + preview_suffix + version_suffix)}</text>
  <rect x="60" y="118" width="360" height="{height - 178}" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="78" y="166" font-size="42" font-weight="800" fill="{tokens["text"]}">{escape(model.player_name)}</text>
  <text x="78" y="194" font-size="13" fill="{tokens["muted"]}" letter-spacing="1.2">UID: {model.uid}{escape(version_suffix)}</text>
  {"".join(info_rows)}
  <text x="78" y="528" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">Position Scores</text>
  {"".join(position_chips)}
  <text x="78" y="{top_chip_y - 18}" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">Top Positions</text>
  {"".join(top_position_chips)}
  {habits_block}
  <rect x="444" y="118" width="302" height="438" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <rect x="764" y="118" width="302" height="438" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <rect x="1084" y="118" width="302" height="438" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  {_render_svg_group(model.attribute_groups[0], x=444, y=118, width=302, text_fill=tokens["text"], muted_fill=tokens["muted"], line_fill=tokens["line"], bar_fill="url(#bar-gradient)")}
  {_render_svg_group(model.attribute_groups[1], x=764, y=118, width=302, text_fill=tokens["text"], muted_fill=tokens["muted"], line_fill=tokens["line"], bar_fill="url(#bar-gradient)")}
  {_render_svg_group(model.attribute_groups[2], x=1084, y=118, width=302, text_fill=tokens["text"], muted_fill=tokens["muted"], line_fill=tokens["line"], bar_fill="url(#bar-gradient)")}
  <rect x="444" y="578" width="542" height="620" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <rect x="1006" y="578" width="380" height="620" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  {_render_svg_group(model.attribute_groups[3], x=444, y=578, width=542, text_fill=tokens["text"], muted_fill=tokens["muted"], line_fill=tokens["line"], bar_fill="url(#bar-gradient)")}
  <text x="1024" y="614" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">Radar Summary</text>
  {"".join(radar_rows)}
  {"".join(grid_rings)}
  {"".join(radar_axes)}
  {"".join(radar_labels)}
  <polygon points="{radar_polygon}" fill="rgba(96,165,250,0.30)" stroke="#60a5fa" stroke-width="2" />
</svg>"""


def _render_info_rows(rows, *, x: int, start_y: int, label_fill: str, value_fill: str, line_fill: str, width: int, row_height: int = 38) -> str:
    parts: list[str] = []
    current_y = start_y
    for row in rows:
        parts.append(
            f'<text x="{x}" y="{current_y}" font-size="13" fill="{label_fill}">{escape(row.label)}</text>'
            f'<text x="{x + width}" y="{current_y}" font-size="15" font-weight="700" fill="{value_fill}" text-anchor="end">{escape(row.value)}</text>'
            f'<line x1="{x}" y1="{current_y + 14}" x2="{x + width}" y2="{current_y + 14}" stroke="{line_fill}" />'
        )
        current_y += row_height
    return "".join(parts)


def build_wage_share_svg(player: PlayerAttributeDetailResponse, wage_detail: WageDetailResponse, *, theme: str = "dark") -> str:
    model: WageShareCardModel = build_wage_share_card_model(player, wage_detail, theme=theme)
    tokens = _theme_tokens(model.theme)
    width = model.canvas_width
    height = model.canvas_height
    summary_rows = _render_info_rows(model.summary_rows, x=82, start_y=270, label_fill=tokens["muted"], value_fill=tokens["text"], line_fill=tokens["line"], width=320)
    formula_rows = _render_info_rows(model.formula_rows, x=520, start_y=286, label_fill=tokens["muted"], value_fill=tokens["text"], line_fill=tokens["line"], width=820, row_height=42)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="wage-bg-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{tokens["bg"]}" />
      <stop offset="100%" stop-color="{tokens["bg_2"]}" />
    </linearGradient>
    <linearGradient id="wage-accent-gradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{tokens["accent"]}" />
      <stop offset="100%" stop-color="{tokens["accent_2"]}" />
    </linearGradient>
    <style>
      text {{ font-family: {SHARE_FONT_FAMILY}; }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#wage-bg-gradient)" />
  <rect x="30" y="30" width="{width - 60}" height="{height - 60}" rx="28" fill="{tokens["panel"]}" stroke="{tokens["line"]}" />
  <rect x="60" y="60" width="160" height="34" rx="17" fill="{tokens["accent_soft"]}" />
  <text x="140" y="82" font-size="13" font-weight="800" fill="{tokens["accent"]}" text-anchor="middle" letter-spacing="1.5">HEIGO WAGE CARD</text>
  <text x="{width - 70}" y="84" font-size="13" font-weight="700" fill="{tokens["muted"]}" text-anchor="end">Slot {escape(model.slot_type_label)}</text>
  <rect x="60" y="122" width="380" height="{height - 182}" rx="24" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="82" y="174" font-size="44" font-weight="800" fill="{tokens["text"]}">{escape(model.player_name)}</text>
  <text x="82" y="206" font-size="14" fill="{tokens["muted"]}" letter-spacing="1.2">UID {model.uid} | {escape(model.position)} | Age {escape(model.age_label)}</text>
  <rect x="82" y="224" width="190" height="88" rx="22" fill="url(#wage-accent-gradient)" />
  <text x="104" y="256" font-size="14" font-weight="700" fill="#ffffff" letter-spacing="1.0">CURRENT WAGE</text>
  <text x="104" y="292" font-size="32" font-weight="800" fill="#ffffff">{escape(model.headline_value)}</text>
  {summary_rows}
  <rect x="472" y="122" width="908" height="{height - 182}" rx="24" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="520" y="178" font-size="18" font-weight="800" fill="{tokens["text"]}">Wage Calculation</text>
  <text x="520" y="210" font-size="14" fill="{tokens["muted"]}">Club {escape(model.team_name)} | Position {escape(model.position)}</text>
  <rect x="520" y="236" width="820" height="1" fill="{tokens["line"]}" />
  {formula_rows}
</svg>"""


def _render_roster_table_rows(rows: tuple[RosterPlayerRow, ...], *, x: int, start_y: int, width: int, tokens: dict[str, str]) -> str:
    rendered: list[str] = []
    row_height = 48
    for index, row in enumerate(rows):
        y = start_y + index * row_height
        fill = tokens["panel_soft"] if index % 2 == 0 else "rgba(255,255,255,0.02)"
        rendered.append(
            f'<rect x="{x}" y="{y - 22}" width="{width}" height="38" rx="12" fill="{fill}" stroke="{tokens["line"]}" />'
            f'<text x="{x + 18}" y="{y}" font-size="13" fill="{tokens["muted"]}">{row.index}</text>'
            f'<text x="{x + 64}" y="{y}" font-size="14" font-weight="700" fill="{tokens["text"]}">{escape(row.name)}</text>'
            f'<text x="{x + 420}" y="{y}" font-size="13" fill="{tokens["text"]}">{escape(row.position)}</text>'
            f'<text x="{x + 540}" y="{y}" font-size="13" fill="{tokens["text"]}">{escape(row.age_label)}</text>'
            f'<text x="{x + 680}" y="{y}" font-size="13" fill="{tokens["text"]}">{escape(row.ca_pa_label)}</text>'
            f'<text x="{x + 860}" y="{y}" font-size="13" fill="{tokens["text"]}" text-anchor="end">{escape(row.wage_label)}</text>'
            f'<text x="{x + width - 24}" y="{y}" font-size="13" font-weight="700" fill="{tokens["accent"]}" text-anchor="end">{escape(row.slot_type_label)}</text>'
        )
    return "".join(rendered)


def build_roster_share_svg(team_name: str, players: list[PlayerResponse], *, team_info: TeamInfoResponse | None = None, page: int = 1, theme: str = "dark") -> str:
    model: RosterShareCardModel = build_roster_share_card_model(team_name, players, team_info=team_info, page=page, theme=theme)
    tokens = _theme_tokens(model.theme)
    width = model.canvas_width
    height = model.canvas_height
    summary_rows = _render_info_rows(model.summary_rows, x=992, start_y=248, label_fill=tokens["muted"], value_fill=tokens["text"], line_fill=tokens["line"], width=340, row_height=38)
    table_rows = _render_roster_table_rows(model.player_rows, x=82, start_y=320, width=860, tokens=tokens)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="roster-bg-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{tokens["bg"]}" />
      <stop offset="100%" stop-color="{tokens["bg_2"]}" />
    </linearGradient>
    <style>
      text {{ font-family: {SHARE_FONT_FAMILY}; }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#roster-bg-gradient)" />
  <rect x="30" y="30" width="{width - 60}" height="{height - 60}" rx="28" fill="{tokens["panel"]}" stroke="{tokens["line"]}" />
  <rect x="60" y="60" width="150" height="34" rx="17" fill="{tokens["accent_soft"]}" />
  <text x="135" y="82" font-size="13" font-weight="800" fill="{tokens["accent"]}" text-anchor="middle" letter-spacing="1.5">HEIGO ROSTER</text>
  <text x="82" y="164" font-size="42" font-weight="800" fill="{tokens["text"]}">{escape(model.team_name)}</text>
  <text x="82" y="198" font-size="14" fill="{tokens["muted"]}">Manager {escape(model.manager_name)} | Level {escape(model.level_label)}</text>
  <text x="{width - 74}" y="82" font-size="13" font-weight="700" fill="{tokens["muted"]}" text-anchor="end">Page {model.page}/{model.total_pages} | Players {model.total_players}</text>
  <rect x="60" y="228" width="902" height="{height - 288}" rx="24" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="100" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4">#</text>
  <text x="146" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4">NAME</text>
  <text x="500" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4">POSITION</text>
  <text x="620" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4">AGE</text>
  <text x="760" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4">CA / PA</text>
  <text x="940" y="276" font-size="12" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.4" text-anchor="end">WAGE</text>
  {table_rows}
  <rect x="982" y="228" width="358" height="{height - 288}" rx="24" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="1014" y="180" font-size="18" font-weight="800" fill="{tokens["text"]}">Team Snapshot</text>
  {summary_rows}
</svg>"""
