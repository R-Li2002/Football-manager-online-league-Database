from __future__ import annotations

from html import escape
from math import cos, pi, sin

from schemas_read import PlayerAttributeDetailResponse, PlayerResponse, TeamInfoResponse, WageDetailResponse
from services.share_card_model_service import (
    RosterPlayerRow,
    RosterShareCardModel,
    SHARE_FONT_FAMILY,
    ShareGroup,
    ShareMetric,
    SharePositionMarker,
    WageShareCardModel,
    build_player_share_card_model,
    build_roster_share_card_model,
    build_wage_share_card_model,
)


def _theme_tokens(theme: str) -> dict[str, str]:
    if theme == "light":
        return {
            "bg": "#edf2fb",
            "bg_2": "#f8fbff",
            "panel": "rgba(255,255,255,0.98)",
            "panel_soft": "rgba(255,255,255,0.94)",
            "line": "rgba(76,79,105,0.10)",
            "line_soft": "rgba(76,79,105,0.08)",
            "text": "#2c3650",
            "muted": "#6c6f85",
            "accent": "#1e66f5",
            "accent_2": "#27ae60",
            "accent_soft": "rgba(30,102,245,0.08)",
            "real_club": "#2980b9",
            "heigo_club": "#27ae60",
            "pitch_top": "rgba(166,196,183,0.92)",
            "pitch_bottom": "rgba(129,170,153,0.95)",
            "pitch_line": "rgba(255,255,255,0.42)",
            "shadow": "rgba(76,79,105,0.14)",
        }
    return {
        "bg": "#141822",
        "bg_2": "#0c1019",
        "panel": "rgba(16,22,34,0.998)",
        "panel_soft": "rgba(34,40,58,0.84)",
        "line": "rgba(192,202,245,0.10)",
        "line_soft": "rgba(192,202,245,0.07)",
        "text": "#d9e3ff",
        "muted": "#a6b2d2",
        "accent": "#7aa2f7",
        "accent_2": "#34d399",
        "accent_soft": "rgba(122,162,247,0.12)",
        "real_club": "#1fd1ff",
        "heigo_club": "#22dd88",
        "pitch_top": "rgba(36,90,72,0.90)",
        "pitch_bottom": "rgba(18,55,47,0.94)",
        "pitch_line": "rgba(255,255,255,0.24)",
        "shadow": "rgba(4,8,16,0.36)",
    }


def _tier_palette(value: float, *, theme: str) -> tuple[str, str]:
    numeric = max(1, min(20, int(value or 0)))
    if theme == "light":
        palettes = [
            (4, "#5C4B51", "#5C4B51"),
            (8, "#5f978a", "#5f978a"),
            (12, "#9c8f4f", "#9c8f4f"),
            (16, "#c7802e", "#c7802e"),
            (20, "#d94f4f", "#d94f4f"),
        ]
    else:
        palettes = [
            (4, "#5C4B51", "#c5aeb4"),
            (8, "#8CBEB2", "#8CBEB2"),
            (12, "#F2EBBF", "#F2EBBF"),
            (16, "#F3B562", "#F3B562"),
            (20, "#F06060", "#F06060"),
        ]
    for limit, accent, value_fill in palettes:
        if numeric <= limit:
            return accent, value_fill
    return palettes[-1][1], palettes[-1][2]


def _position_marker_fill(score: int) -> str:
    if score <= 1:
        return "#8f96a3"
    if score <= 9:
        return "#F06060"
    if score <= 14:
        return "#F3B562"
    return "#34c759"


def _wrap_text(value: str, max_units: int) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []
    lines: list[str] = []
    current = ""
    current_units = 0
    for ch in text:
        units = 1 if ord(ch) < 128 else 2
        if current and current_units + units > max_units:
            lines.append(current)
            current = ch
            current_units = units
            continue
        current += ch
        current_units += units
    if current:
        lines.append(current)
    return lines


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


def _render_reaction_pills(*, x: int, y: int, model, theme: str) -> str:
    if model.reaction_flower_count <= 0 and model.reaction_egg_count <= 0:
        return ""
    flower_bg = "rgba(249,168,212,0.16)" if theme == "dark" else "rgba(255,236,244,0.96)"
    egg_bg = "rgba(251,191,36,0.14)" if theme == "dark" else "rgba(255,247,220,0.98)"
    flower_border = "rgba(244,114,182,0.26)"
    egg_border = "rgba(245,158,11,0.24)"
    text_fill = "#f4f7fb" if theme == "dark" else "#4c4f69"
    count_bg = "rgba(255,255,255,0.14)" if theme == "dark" else "rgba(76,79,105,0.08)"
    return (
        f'<rect x="{x}" y="{y}" width="74" height="34" rx="17" fill="{flower_bg}" stroke="{flower_border}" />'
        f'<circle cx="{x + 20}" cy="{y + 17}" r="7" fill="#ff9fbe" />'
        f'<circle cx="{x + 20}" cy="{y + 10}" r="4" fill="#ff9fbe" />'
        f'<circle cx="{x + 27}" cy="{y + 17}" r="4" fill="#ff9fbe" />'
        f'<circle cx="{x + 20}" cy="{y + 24}" r="4" fill="#ff9fbe" />'
        f'<circle cx="{x + 13}" cy="{y + 17}" r="4" fill="#ff9fbe" />'
        f'<circle cx="{x + 20}" cy="{y + 17}" r="3" fill="#8fe388" />'
        f'<rect x="{x + 40}" y="{y + 8}" width="22" height="18" rx="9" fill="{count_bg}" />'
        f'<text x="{x + 51}" y="{y + 21}" font-size="12" font-weight="700" fill="{text_fill}" text-anchor="middle">{model.reaction_flower_count}</text>'
        f'<rect x="{x + 84}" y="{y}" width="74" height="34" rx="17" fill="{egg_bg}" stroke="{egg_border}" />'
        f'<ellipse cx="{x + 104}" cy="{y + 17}" rx="7" ry="9" fill="#ffe8ae" stroke="rgba(223,142,29,0.4)" />'
        f'<rect x="{x + 124}" y="{y + 8}" width="22" height="18" rx="9" fill="{count_bg}" />'
        f'<text x="{x + 135}" y="{y + 21}" font-size="12" font-weight="700" fill="{text_fill}" text-anchor="middle">{model.reaction_egg_count}</text>'
    )


def _render_player_info_rows(*, model, x: int, y: int, width: int, tokens: dict[str, str]) -> str:
    rows: list[str] = []
    current_y = y
    for row in model.info_rows:
        value_fill = tokens["text"]
        if row.label == "HEIGO俱乐部" and row.value != "大海":
            value_fill = tokens["heigo_club"]
        elif row.label == "现实俱乐部":
            value_fill = tokens["real_club"]
        rows.append(
            f'<text x="{x}" y="{current_y}" font-size="12.5" fill="{tokens["muted"]}">{escape(row.label)}</text>'
            f'<text x="{x + width}" y="{current_y}" font-size="14.5" font-weight="700" fill="{value_fill}" text-anchor="end">{escape(row.value)}</text>'
            f'<line x1="{x}" y1="{current_y + 12}" x2="{x + width}" y2="{current_y + 12}" stroke="{tokens["line"]}" />'
        )
        current_y += 38
    return "".join(rows)


def _render_position_map(*, x: int, y: int, width: int, markers: tuple[SharePositionMarker, ...], tokens: dict[str, str]) -> str:
    board_x = x
    board_y = y + 18
    board_w = width
    board_h = 244
    field_x = board_x + 10
    field_y = board_y + 10
    field_w = board_w - 20
    field_h = board_h - 20
    parts = [
        f'<text x="{x}" y="{y}" font-size="12.5" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1">位置熟练度图</text>',
        f'<rect x="{board_x}" y="{board_y}" width="{board_w}" height="{board_h}" rx="12" fill="rgba(255,255,255,0.04)" stroke="{tokens["line_soft"]}" />',
        f'<defs><linearGradient id="pitch-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{tokens["pitch_top"]}" /><stop offset="100%" stop-color="{tokens["pitch_bottom"]}" /></linearGradient></defs>',
        f'<rect x="{field_x}" y="{field_y}" width="{field_w}" height="{field_h}" rx="10" fill="url(#pitch-gradient)" stroke="{tokens["line_soft"]}" />',
    ]
    stripe_h = field_h / 8.0
    for idx in range(8):
        if idx % 2 == 0:
            parts.append(
                f'<rect x="{field_x}" y="{field_y + idx * stripe_h:.1f}" width="{field_w}" height="{stripe_h:.1f}" fill="rgba(255,255,255,0.03)" />'
            )
    parts.extend(
        [
            f'<line x1="{field_x}" y1="{field_y + field_h / 2:.1f}" x2="{field_x + field_w}" y2="{field_y + field_h / 2:.1f}" stroke="{tokens["pitch_line"]}" />',
            f'<circle cx="{field_x + field_w / 2:.1f}" cy="{field_y + field_h / 2:.1f}" r="34" fill="none" stroke="{tokens["pitch_line"]}" />',
            f'<circle cx="{field_x + field_w / 2:.1f}" cy="{field_y + field_h / 2:.1f}" r="2.5" fill="{tokens["pitch_line"]}" />',
            f'<path d="M {field_x + field_w * 0.19:.1f} {field_y} H {field_x + field_w * 0.81:.1f} V {field_y + 58:.1f} Q {field_x + field_w * 0.81:.1f} {field_y + 76:.1f} {field_x + field_w * 0.76:.1f} {field_y + 76:.1f} H {field_x + field_w * 0.24:.1f} Q {field_x + field_w * 0.19:.1f} {field_y + 76:.1f} {field_x + field_w * 0.19:.1f} {field_y + 58:.1f} Z" fill="none" stroke="{tokens["pitch_line"]}" />',
            f'<path d="M {field_x + field_w * 0.34:.1f} {field_y} H {field_x + field_w * 0.66:.1f} V {field_y + 26:.1f} Q {field_x + field_w * 0.66:.1f} {field_y + 38:.1f} {field_x + field_w * 0.62:.1f} {field_y + 38:.1f} H {field_x + field_w * 0.38:.1f} Q {field_x + field_w * 0.34:.1f} {field_y + 38:.1f} {field_x + field_w * 0.34:.1f} {field_y + 26:.1f} Z" fill="none" stroke="{tokens["pitch_line"]}" />',
            f'<path d="M {field_x + field_w * 0.19:.1f} {field_y + field_h:.1f} H {field_x + field_w * 0.81:.1f} V {field_y + field_h - 58:.1f} Q {field_x + field_w * 0.81:.1f} {field_y + field_h - 76:.1f} {field_x + field_w * 0.76:.1f} {field_y + field_h - 76:.1f} H {field_x + field_w * 0.24:.1f} Q {field_x + field_w * 0.19:.1f} {field_y + field_h - 76:.1f} {field_x + field_w * 0.19:.1f} {field_y + field_h - 58:.1f} Z" fill="none" stroke="{tokens["pitch_line"]}" />',
            f'<path d="M {field_x + field_w * 0.34:.1f} {field_y + field_h:.1f} H {field_x + field_w * 0.66:.1f} V {field_y + field_h - 26:.1f} Q {field_x + field_w * 0.66:.1f} {field_y + field_h - 38:.1f} {field_x + field_w * 0.62:.1f} {field_y + field_h - 38:.1f} H {field_x + field_w * 0.38:.1f} Q {field_x + field_w * 0.34:.1f} {field_y + field_h - 38:.1f} {field_x + field_w * 0.34:.1f} {field_y + field_h - 26:.1f} Z" fill="none" stroke="{tokens["pitch_line"]}" />',
        ]
    )
    for marker in markers:
        marker_x = field_x + field_w * marker.x_percent / 100.0
        marker_y = field_y + field_h * marker.y_percent / 100.0
        parts.extend(
            [
                f'<circle cx="{marker_x:.1f}" cy="{marker_y:.1f}" r="12" fill="{_position_marker_fill(marker.score)}" stroke="rgba(255,255,255,0.18)" />',
                f'<text x="{marker_x:.1f}" y="{marker_y + 4:.1f}" font-size="9.5" font-weight="800" fill="#ffffff" text-anchor="middle">{escape(marker.label)}</text>',
            ]
        )
    return "".join(parts)


def _render_radar(*, metrics: tuple[ShareMetric, ...], x: int, y: int, size: int, tokens: dict[str, str]) -> str:
    center_x = x + size / 2.0
    center_y = y + size / 2.0
    radius = size * 0.28
    label_radius = size * 0.36
    axis_points = _radar_axis_points(len(metrics), center_x=center_x, center_y=center_y, radius=radius)
    rings: list[str] = []
    for scale in (0.2, 0.4, 0.6, 0.8, 1.0):
        ring_points = []
        for point_x, point_y in axis_points:
            ring_points.append(f"{center_x + (point_x - center_x) * scale:.1f},{center_y + (point_y - center_y) * scale:.1f}")
        rings.append(f'<polygon points="{" ".join(ring_points)}" fill="none" stroke="{tokens["line_soft"]}" stroke-width="1" />')
    axes: list[str] = []
    labels: list[str] = []
    points: list[str] = []
    point_marks: list[str] = []
    for index, metric in enumerate(metrics):
        edge_x, edge_y = axis_points[index]
        axes.append(f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{edge_x:.1f}" y2="{edge_y:.1f}" stroke="{tokens["line_soft"]}" />')
        label_x = center_x + (edge_x - center_x) * (label_radius / radius)
        label_y = center_y + (edge_y - center_y) * (label_radius / radius)
        anchor = "middle"
        if label_x < center_x - 12:
            anchor = "end"
        elif label_x > center_x + 12:
            anchor = "start"
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y + (10 if label_y > center_y else -4):.1f}" font-size="10" font-weight="600" fill="{tokens["muted"]}" text-anchor="{anchor}">{escape(metric.label)}</text>'
        )
        scale = max(0.0, min(1.0, metric.value / 20.0))
        px = center_x + cos((-pi / 2) + (2 * pi * index / len(metrics))) * radius * scale
        py = center_y + sin((-pi / 2) + (2 * pi * index / len(metrics))) * radius * scale
        points.append(f"{px:.1f},{py:.1f}")
        point_marks.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#f8fafc" stroke="{tokens["accent"]}" stroke-width="1.35" />')
    return "".join(
        [
            *rings,
            *axes,
            f'<polygon points="{" ".join(points)}" fill="rgba(122,162,247,0.18)" stroke="rgba(122,162,247,0.94)" stroke-width="1.8" />',
            *point_marks,
            *labels,
        ]
    )


def _render_attribute_group(
    group: ShareGroup,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    tokens: dict[str, str],
    theme: str,
    include_radar: bool = False,
    radar_metrics: tuple[ShareMetric, ...] = (),
) -> str:
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="16" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />',
        f'<text x="{x + 16}" y="{y + 26}" font-size="13" font-weight="700" fill="{tokens["muted"]}">{escape(group.title)}</text>',
    ]
    row_y = y + 58
    row_height = 30
    content_limit_y = (y + 392) if include_radar else (y + height - 14)
    for item in group.items:
        accent, value_fill = _tier_palette(item.value, theme=theme)
        parts.extend(
            [
                f'<rect x="{x + 12}" y="{row_y - 16}" width="{width - 24}" height="24" rx="6" fill="rgba(255,255,255,0.03)" stroke="{tokens["line_soft"]}" />',
                f'<rect x="{x + 12}" y="{row_y - 16}" width="2.5" height="24" rx="1.25" fill="{accent}" />',
                f'<text x="{x + 22}" y="{row_y}" font-size="11.5" font-weight="700" fill="{tokens["text"]}">{escape(item.label)}</text>',
                f'<text x="{x + width - 18}" y="{row_y}" font-size="12.5" font-weight="800" fill="{value_fill}" text-anchor="end">{int(round(item.value))}</text>',
            ]
        )
        row_y += row_height
        if row_y > content_limit_y:
            break
    if include_radar and radar_metrics:
        divider_y = y + 344
        radar_size = width - 120
        radar_x = x + (width - radar_size) / 2
        radar_y = divider_y + 18
        parts.extend(
            [
                f'<line x1="{x + 16}" y1="{divider_y}" x2="{x + width - 16}" y2="{divider_y}" stroke="{tokens["line"]}" />',
                f'<text x="{x + 16}" y="{divider_y + 20}" font-size="12" font-weight="700" fill="{tokens["muted"]}">能力雷达</text>',
                _render_radar(metrics=radar_metrics, x=radar_x, y=radar_y, size=radar_size, tokens=tokens),
            ]
        )
    return "".join(parts)


def _render_hidden_group(group: ShareGroup, *, x: int, y: int, width: int, height: int, tokens: dict[str, str], theme: str) -> str:
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="16" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />',
        f'<text x="{x + 16}" y="{y + 26}" font-size="13" font-weight="700" fill="{tokens["muted"]}">{escape(group.title)}</text>',
    ]
    columns = 3
    col_width = (width - 48) / columns
    row_height = 36
    for index, item in enumerate(group.items):
        col = index % columns
        row = index // columns
        item_x = x + 16 + col * col_width
        item_y = y + 50 + row * row_height
        accent, value_fill = _tier_palette(item.value, theme=theme)
        parts.extend(
            [
                f'<rect x="{item_x:.1f}" y="{item_y - 16:.1f}" width="{col_width - 10:.1f}" height="24" rx="6" fill="rgba(255,255,255,0.03)" stroke="{tokens["line_soft"]}" />',
                f'<rect x="{item_x:.1f}" y="{item_y - 16:.1f}" width="2.5" height="24" rx="1.25" fill="{accent}" />',
                f'<text x="{item_x + 10:.1f}" y="{item_y:.1f}" font-size="11.5" font-weight="700" fill="{tokens["text"]}">{escape(item.label)}</text>',
                f'<text x="{item_x + col_width - 18:.1f}" y="{item_y:.1f}" font-size="12.5" font-weight="800" fill="{value_fill}" text-anchor="end">{int(round(item.value))}</text>',
            ]
        )
    return "".join(parts)


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
    preview_copy = model.preview_label + (f" · {model.weak_foot_label}" if model.weak_foot_label else "")
    version_copy = f" · {model.version_label}" if model.version_label else ""
    habits = _wrap_text(model.habit_text, 34)
    left_x = 54
    left_y = 104
    left_w = 360
    left_h = height - 152
    group_y = 104
    group_w = 308
    group_h = 560
    hidden_y = 680
    hidden_h = height - hidden_y - 48
    reactions_svg = _render_reaction_pills(x=left_x + 20, y=left_y + 96, model=model, theme=model.theme)
    has_reactions = bool(reactions_svg)
    info_y = left_y + (154 if has_reactions else 124)
    position_map_y = left_y + (512 if has_reactions else 482)
    habit_y = position_map_y + 286
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="page-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{tokens["bg"]}" />
      <stop offset="100%" stop-color="{tokens["bg_2"]}" />
    </linearGradient>
    <style>
      text {{ font-family: {SHARE_FONT_FAMILY}; dominant-baseline: alphabetic; }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#page-bg)" />
  <circle cx="148" cy="90" r="180" fill="rgba(122,162,247,0.16)" />
  <circle cx="1286" cy="78" r="150" fill="rgba(52,211,153,0.10)" />
  <rect x="24" y="24" width="{width - 48}" height="{height - 48}" rx="30" fill="rgba(255,255,255,0.02)" />
  <text x="54" y="66" font-size="12" font-weight="700" fill="{tokens["muted"]}">HEIGO 球员详情图</text>
  <text x="{width - 54}" y="66" font-size="12" font-weight="700" fill="{tokens["muted"]}" text-anchor="end">{escape(preview_copy + version_copy)}</text>
  <rect x="{left_x}" y="{left_y}" width="{left_w}" height="{left_h}" rx="18" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="{left_x + 20}" y="{left_y + 46}" font-size="28" font-weight="800" fill="{tokens["text"]}">{escape(model.player_name)}</text>
  <text x="{left_x + 20}" y="{left_y + 76}" font-size="14" fill="{tokens["muted"]}">UID: {model.uid}{escape(version_copy)}</text>
  {reactions_svg}
  {_render_player_info_rows(model=model, x=left_x + 20, y=info_y, width=left_w - 40, tokens=tokens)}
  {_render_position_map(x=left_x + 20, y=position_map_y, width=left_w - 40, markers=model.position_markers, tokens=tokens)}
  {''.join(f'<text x="{left_x + 20}" y="{habit_y + index * 22}" font-size="12.5" fill="{tokens["muted"] if index == 0 else tokens["text"]}">{escape(line)}</text>' for index, line in enumerate((["球员习惯"] + habits[:2]) if habits else []))}
  {_render_attribute_group(model.attribute_groups[0], x=430, y=group_y, width=group_w, height=group_h, tokens=tokens, theme=model.theme)}
  {_render_attribute_group(model.attribute_groups[1], x=754, y=group_y, width=group_w, height=group_h, tokens=tokens, theme=model.theme)}
  {_render_attribute_group(model.attribute_groups[2], x=1078, y=group_y, width=group_w, height=group_h, tokens=tokens, theme=model.theme, include_radar=True, radar_metrics=model.radar_metrics)}
  {_render_hidden_group(model.attribute_groups[3], x=430, y=hidden_y, width=956, height=hidden_h, tokens=tokens, theme=model.theme)}
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
