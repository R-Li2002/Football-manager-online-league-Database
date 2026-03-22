from __future__ import annotations

from html import escape

from schemas_read import PlayerAttributeDetailResponse
from services.share_card_model_service import (
    SHARE_FONT_FAMILY,
    ShareCardModel,
    ShareChip,
    ShareGroup,
    build_player_share_card_model,
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


def _render_html_chips(chips: tuple[ShareChip, ...], empty_copy: str) -> str:
    if not chips:
        return f'<div class="muted">{escape(empty_copy)}</div>'
    return "".join(
        f'<span class="chip"><strong>{escape(chip.label)}</strong> {escape(chip.value)}</span>'
        for chip in chips
    )


def _render_html_group(group: ShareGroup, *, fill_class: str = "attr-bar-fill") -> str:
    rows = []
    for item in group.items:
        rows.append(
            f"""
            <div class="attr-row">
                <span class="attr-label">{escape(item.label)}</span>
                <span class="attr-value">{int(round(item.value))}</span>
                <span class="attr-bar"><span class="{fill_class}" style="width:{item.percent}%"></span></span>
            </div>
            """
        )
    return f'<section class="group-card"><h3>{escape(group.title)}</h3>{"".join(rows)}</section>'


def _render_html_radar_metrics(model: ShareCardModel) -> str:
    rows = []
    for item in model.radar_metrics:
        rows.append(
            f"""
            <div class="metric-row">
                <span class="metric-label">{escape(item.label)}</span>
                <span class="metric-value">{item.value:.1f}</span>
                <span class="attr-bar"><span class="metric-fill" style="width:{item.percent}%"></span></span>
            </div>
            """
        )
    return "".join(rows)


def build_player_share_page_html(
    player: PlayerAttributeDetailResponse,
    *,
    version: str | None = None,
    step: int = 0,
    theme: str = "dark",
) -> str:
    model = build_player_share_card_model(player, version=version, step=step, theme=theme)
    tokens = _theme_tokens(model.theme)
    version_suffix = f" | {escape(model.version_label)}" if model.version_label else ""
    weak_foot_copy = f" | {escape(model.weak_foot_label)}" if model.weak_foot_label else ""
    habits_block = ""
    if model.habit_text:
        habits_block = f"""
        <section class="info-card">
            <h3>Player Traits</h3>
            <p class="habit-copy">{escape(model.habit_text)}</p>
        </section>
        """

    info_rows_markup = "".join(
        f'<div class="info-row"><span class="label">{escape(row.label)}</span><span class="value">{escape(row.value)}</span></div>'
        for row in model.info_rows
    )
    attribute_groups = "".join(_render_html_group(group) for group in model.attribute_groups[:3])
    hidden_group = _render_html_group(model.attribute_groups[3])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(model.player_name)} - HEIGO Share</title>
    <style>
        :root {{
            color-scheme: {"light" if model.theme == "light" else "dark"};
            --bg: {tokens["bg"]};
            --panel: {tokens["panel"]};
            --panel-soft: {tokens["panel_soft"]};
            --line: {tokens["line"]};
            --text: {tokens["text"]};
            --muted: {tokens["muted"]};
            --accent: {tokens["accent"]};
            --accent-2: {tokens["accent_2"]};
            --accent-soft: {tokens["accent_soft"]};
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background:
                radial-gradient(circle at top left, rgba(56,189,248,0.14), transparent 28%),
                radial-gradient(circle at top right, rgba(34,197,94,0.12), transparent 24%),
                var(--bg);
            color: var(--text);
            font-family: {SHARE_FONT_FAMILY};
        }}
        .page {{ width: 1440px; margin: 0 auto; padding: 28px; }}
        .card {{
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
        }}
        .topbar {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 18px; }}
        .eyebrow {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            background: var(--accent-soft);
            color: var(--accent);
        }}
        .preview {{ color: var(--muted); font-size: 13px; font-weight: 700; }}
        .layout {{ display: grid; grid-template-columns: 340px minmax(0, 1fr); gap: 16px; }}
        .info-card, .group-card, .metric-card {{
            border: 1px solid var(--line);
            background: var(--panel-soft);
            border-radius: 18px;
            padding: 16px;
        }}
        .identity h1 {{ margin: 0 0 8px; font-size: 40px; line-height: 1; }}
        .uid {{ color: var(--muted); font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }}
        .info-list {{ display: grid; gap: 8px; margin-top: 16px; }}
        .info-row {{ display: grid; grid-template-columns: 110px 1fr; gap: 12px; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--line); }}
        .info-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .label {{ color: var(--muted); font-size: 13px; }}
        .value {{ text-align: right; font-weight: 700; }}
        .chip-wrap {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .chip {{
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.04);
            font-size: 13px;
        }}
        .main-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
        .group-card h3, .info-card h3, .metric-card h3 {{ margin: 0 0 12px; font-size: 13px; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; }}
        .attr-row, .metric-row {{ display: grid; grid-template-columns: 110px 36px 1fr; gap: 10px; align-items: center; margin-bottom: 8px; }}
        .attr-row:last-child, .metric-row:last-child {{ margin-bottom: 0; }}
        .attr-label, .metric-label {{ font-size: 13px; }}
        .attr-value, .metric-value {{ text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }}
        .attr-bar {{ height: 10px; background: rgba(148, 163, 184, 0.14); border-radius: 999px; overflow: hidden; }}
        .attr-bar-fill, .metric-fill {{ display: block; height: 100%; border-radius: inherit; }}
        .attr-bar-fill {{ background: linear-gradient(90deg, var(--accent), var(--accent-2)); }}
        .metric-fill {{ background: linear-gradient(90deg, #60a5fa, #22d3ee); }}
        .muted {{ color: var(--muted); font-size: 13px; }}
        .habit-copy {{ margin: 0; line-height: 1.6; color: var(--text); }}
    </style>
</head>
<body>
    <main class="page">
        <section class="card">
            <div class="topbar">
                <div><span class="eyebrow">HEIGO PLAYER SHARE</span></div>
                <div class="preview">{escape(model.preview_label)}{weak_foot_copy}{version_suffix}</div>
            </div>
            <div class="layout">
                <aside>
                    <section class="info-card identity">
                        <h1>{escape(model.player_name)}</h1>
                        <div class="uid">UID: {model.uid}{version_suffix}</div>
                        <div class="info-list">{info_rows_markup}</div>
                    </section>
                    <section class="info-card">
                        <h3>Position Scores</h3>
                        <div class="chip-wrap">{_render_html_chips(model.position_chips, "No position data")}</div>
                    </section>
                    <section class="info-card">
                        <h3>Top Positions</h3>
                        <div class="chip-wrap">{_render_html_chips(model.top_position_chips, "No top position data")}</div>
                    </section>
                    {habits_block}
                </aside>
                <section>
                    <div class="main-grid">{attribute_groups}</div>
                    <div style="height:14px"></div>
                    <div class="main-grid" style="grid-template-columns: minmax(0, 1fr) 320px;">
                        {hidden_group}
                        <section class="metric-card">
                            <h3>Radar Summary</h3>
                            {_render_html_radar_metrics(model)}
                        </section>
                    </div>
                </section>
            </div>
        </section>
    </main>
</body>
</html>"""
