from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import cos, pi, sin

from schemas_read import PlayerAttributeDetailResponse


HALF_STEP_PREVIEW_KEYS = {"bravery", "leadership"}
STATIC_PREVIEW_KEYS = {"aggression", "determination", "natural_fitness", "flair"}
DETAIL_PREVIEW_KEYS = [
    "reflexes",
    "aerial_ability",
    "kicking",
    "handling",
    "command_of_area",
    "throwing",
    "one_on_ones",
    "communication",
    "tendency_to_punch",
    "rushing_out",
    "eccentricity",
    "passing",
    "crossing",
    "marking",
    "technique",
    "dribbling",
    "tackling",
    "finishing",
    "first_touch",
    "heading",
    "long_shots",
    "penalty",
    "corner",
    "long_throws",
    "free_kick",
    "flair",
    "positioning",
    "work_rate",
    "concentration",
    "decisions",
    "leadership",
    "aggression",
    "vision",
    "teamwork",
    "off_the_ball",
    "determination",
    "bravery",
    "anticipation",
    "composure",
    "acceleration",
    "jumping",
    "agility",
    "stamina",
    "balance",
    "strength",
    "pace",
    "natural_fitness",
    "consistency",
    "adaptability",
    "pressure",
    "ambition",
    "professionalism",
    "important_matches",
    "injury_proneness",
    "versatility",
    "sportsmanship",
    "temperament",
    "loyalty",
]

GOALKEEPER_TECHNICAL_FIELDS = [
    ("reflexes", "反应"),
    ("aerial_ability", "制空能力"),
    ("kicking", "大脚开球"),
    ("handling", "手控球"),
    ("command_of_area", "拦截传中"),
    ("throwing", "手抛球"),
    ("one_on_ones", "一对一"),
    ("communication", "指挥防守"),
    ("tendency_to_punch", "击球倾向"),
    ("rushing_out", "出击"),
    ("eccentricity", "神经指数"),
]
OUTFIELD_TECHNICAL_FIELDS = [
    ("passing", "传球"),
    ("crossing", "传中"),
    ("marking", "盯人"),
    ("technique", "技术"),
    ("dribbling", "盘带"),
    ("tackling", "抢断"),
    ("finishing", "射门"),
    ("first_touch", "停球"),
    ("heading", "头球"),
    ("long_shots", "远射"),
]
SET_PIECE_FIELDS = [
    ("penalty", "罚点球"),
    ("corner", "角球"),
    ("long_throws", "界外球"),
    ("free_kick", "任意球"),
]
MENTAL_FIELDS = [
    ("flair", "想象力"),
    ("positioning", "防守站位"),
    ("work_rate", "工作投入"),
    ("concentration", "集中"),
    ("decisions", "决断"),
    ("leadership", "领导力"),
    ("aggression", "侵略性"),
    ("vision", "视野"),
    ("teamwork", "团队合作"),
    ("off_the_ball", "无球跑动"),
    ("determination", "意志力"),
    ("bravery", "勇敢"),
    ("anticipation", "预判"),
    ("composure", "镇定"),
]
PHYSICAL_FIELDS = [
    ("acceleration", "爆发力"),
    ("jumping", "弹跳"),
    ("agility", "灵活"),
    ("stamina", "耐力"),
    ("balance", "平衡"),
    ("strength", "强壮"),
    ("pace", "速度"),
    ("natural_fitness", "体质"),
]
HIDDEN_FIELDS = [
    ("consistency", "稳定性"),
    ("adaptability", "适应性"),
    ("pressure", "抗压能力"),
    ("ambition", "野心"),
    ("professionalism", "职业素养"),
    ("important_matches", "大赛发挥"),
    ("injury_proneness", "受伤倾向"),
    ("versatility", "多样性"),
    ("sportsmanship", "体育精神"),
    ("temperament", "情绪控制"),
    ("loyalty", "忠诚"),
]
POSITION_FIELDS = [
    ("pos_st", "ST"),
    ("pos_aml", "AML"),
    ("pos_amc", "AMC"),
    ("pos_amr", "AMR"),
    ("pos_ml", "ML"),
    ("pos_mc", "MC"),
    ("pos_mr", "MR"),
    ("pos_dm", "DM"),
    ("pos_wbl", "WBL"),
    ("pos_wbr", "WBR"),
    ("pos_dl", "DL"),
    ("pos_dc", "DC"),
    ("pos_dr", "DR"),
    ("pos_gk", "GK"),
]


@dataclass(frozen=True)
class ShareInfoRow:
    label: str
    value: str


@dataclass(frozen=True)
class ShareChip:
    label: str
    value: str


@dataclass(frozen=True)
class ShareMetric:
    key: str
    label: str
    value: float
    percent: float


@dataclass(frozen=True)
class ShareGroup:
    title: str
    items: tuple[ShareMetric, ...]


@dataclass(frozen=True)
class ShareCardModel:
    player_name: str
    uid: int
    version_label: str
    preview_label: str
    weak_foot_label: str
    theme: str
    is_goalkeeper: bool
    info_rows: tuple[ShareInfoRow, ...]
    position_chips: tuple[ShareChip, ...]
    top_position_chips: tuple[ShareChip, ...]
    attribute_groups: tuple[ShareGroup, ...]
    radar_metrics: tuple[ShareMetric, ...]
    habit_text: str
    canvas_width: int
    canvas_height: int


def _clamp_attribute_value(value: int | float | None) -> int:
    return max(1, min(20, int(value or 0)))


def _clamp_growth_preview_step(step: int | None) -> int:
    return max(0, min(5, int(step or 0)))


def _preview_ca_gain(step: int) -> int:
    lookup = [0, 11, 30, 50, 70, 90]
    return lookup[_clamp_growth_preview_step(step)]


def _weak_foot_preview(player: PlayerAttributeDetailResponse, step: int) -> tuple[str, int] | None:
    if step < 5:
        return None
    left = int(player.left_foot or 0)
    right = int(player.right_foot or 0)
    if not left or not right or left == right:
        return None
    return ("左脚", min(20, left + 1)) if left < right else ("右脚", min(20, right + 1))


def build_preview_player(player: PlayerAttributeDetailResponse, step: int) -> dict:
    preview_step = _clamp_growth_preview_step(step)
    payload = player.model_dump()

    for key in DETAIL_PREVIEW_KEYS:
        base_value = payload.get(key)
        if not isinstance(base_value, int) or base_value <= 0:
            continue
        if key in STATIC_PREVIEW_KEYS:
            payload[key] = _clamp_attribute_value(base_value)
            continue
        gain = preview_step // 2 if key in HALF_STEP_PREVIEW_KEYS else preview_step
        payload[key] = _clamp_attribute_value(base_value + gain)

    weak_foot = _weak_foot_preview(player, preview_step)
    if weak_foot:
        foot_label, foot_value = weak_foot
        if foot_label == "左脚":
            payload["left_foot"] = foot_value
        else:
            payload["right_foot"] = foot_value

    payload["preview_step"] = preview_step
    payload["preview_ca"] = int(player.ca or 0) + _preview_ca_gain(preview_step)
    payload["preview_weak_foot"] = weak_foot
    return payload


def _average_values(values: list[int | float | None]) -> float:
    normalized: list[float] = []
    for value in values:
        numeric = float(value or 0)
        if numeric > 0:
            normalized.append(numeric)
    if not normalized:
        return 0.0
    return round(sum(normalized) / len(normalized), 1)


def _build_radar_metrics(preview_player: dict) -> list[tuple[str, float]]:
    is_goalkeeper = int(preview_player.get("pos_gk") or 0) >= 15
    if is_goalkeeper:
        return [
            ("拦截射门", _average_values([preview_player.get("one_on_ones"), preview_player.get("reflexes")])),
            ("身体", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])),
            ("速度", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])),
            ("精神", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])),
            ("指挥防守", _average_values([preview_player.get("command_of_area"), preview_player.get("communication")])),
            ("意外性", float(preview_player.get("eccentricity") or 0)),
            ("制空", _average_values([preview_player.get("aerial_ability"), preview_player.get("handling")])),
            ("大脚", _average_values([preview_player.get("kicking"), preview_player.get("throwing")])),
        ]

    return [
        ("防守", _average_values([preview_player.get("marking"), preview_player.get("tackling"), preview_player.get("positioning")])),
        ("身体", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])),
        ("速度", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])),
        ("创造", _average_values([preview_player.get("passing"), preview_player.get("flair"), preview_player.get("vision")])),
        ("进攻", _average_values([preview_player.get("finishing"), preview_player.get("composure"), preview_player.get("off_the_ball")])),
        ("技术", _average_values([preview_player.get("dribbling"), preview_player.get("first_touch"), preview_player.get("technique")])),
        ("制空", _average_values([preview_player.get("heading"), preview_player.get("jumping")])),
        ("精神", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])),
    ]


def _metric_percent(value: int | float) -> float:
    return max(0.0, min(100.0, round((float(value or 0) / 20.0) * 100.0, 1)))


def _build_share_group(title: str, fields: list[tuple[str, str]], preview_player: dict) -> ShareGroup:
    items = tuple(
        ShareMetric(
            key=key,
            label=label,
            value=float(int(preview_player.get(key) or 0)),
            percent=_metric_percent(int(preview_player.get(key) or 0)),
        )
        for key, label in fields
    )
    return ShareGroup(title=title, items=items)


def _format_height(value: int | None) -> str:
    return f"{int(value)} cm" if value else "-"


def _build_position_chips(preview_player: dict) -> tuple[ShareChip, ...]:
    chips: list[ShareChip] = []
    for key, label in POSITION_FIELDS:
        value = int(preview_player.get(key) or 0)
        if value <= 1:
            continue
        chips.append(ShareChip(label=label, value=str(value)))
    return tuple(chips)


def _build_top_position_chips(player: PlayerAttributeDetailResponse) -> tuple[ShareChip, ...]:
    return tuple(ShareChip(label=item.position, value=str(int(item.score))) for item in player.top_positions)


def _build_info_rows(player: PlayerAttributeDetailResponse, preview_player: dict) -> tuple[ShareInfoRow, ...]:
    return (
        ShareInfoRow("国籍", player.nationality or "-"),
        ShareInfoRow("年龄", str(player.age or "-")),
        ShareInfoRow("生日", player.birth_date or "未知"),
        ShareInfoRow("位置", player.position or "-"),
        ShareInfoRow("CA / PA", f"{int(preview_player.get('preview_ca') or player.ca or 0)} / {int(player.pa or 0)}"),
        ShareInfoRow("左脚 / 右脚", f"{preview_player.get('left_foot', '-')} / {preview_player.get('right_foot', '-')}"),
        ShareInfoRow("身高", _format_height(player.height)),
        ShareInfoRow("HEIGO俱乐部", player.heigo_club or "-"),
        ShareInfoRow("现实俱乐部", player.club or "-"),
    )


def build_player_share_card_model(
    player: PlayerAttributeDetailResponse,
    *,
    version: str | None = None,
    step: int = 0,
    theme: str = "dark",
) -> ShareCardModel:
    preview_player = build_preview_player(player, step)
    is_goalkeeper = int(preview_player.get("pos_gk") or 0) >= 15
    technical_fields = GOALKEEPER_TECHNICAL_FIELDS if is_goalkeeper else OUTFIELD_TECHNICAL_FIELDS + SET_PIECE_FIELDS
    weak_foot = preview_player.get("preview_weak_foot")
    weak_foot_label = f"{weak_foot[0]}逆足 +1" if weak_foot else ""
    radar_metrics = tuple(
        ShareMetric(
            key=f"radar_{index}",
            label=label,
            value=value,
            percent=_metric_percent(value),
        )
        for index, (label, value) in enumerate(_build_radar_metrics(preview_player))
    )
    habit_text = (player.player_habits or "").strip()
    return ShareCardModel(
        player_name=player.name,
        uid=player.uid,
        version_label=version or player.data_version or "",
        preview_label=f"成长预览 +{_clamp_growth_preview_step(step)}" if _clamp_growth_preview_step(step) > 0 else "当前属性",
        weak_foot_label=weak_foot_label,
        theme="light" if theme == "light" else "dark",
        is_goalkeeper=is_goalkeeper,
        info_rows=_build_info_rows(player, preview_player),
        position_chips=_build_position_chips(preview_player),
        top_position_chips=_build_top_position_chips(player),
        attribute_groups=(
            _build_share_group("技术", technical_fields, preview_player),
            _build_share_group("精神", MENTAL_FIELDS, preview_player),
            _build_share_group("身体", PHYSICAL_FIELDS, preview_player),
            _build_share_group("隐藏", HIDDEN_FIELDS, preview_player),
        ),
        radar_metrics=radar_metrics,
        habit_text=habit_text,
        canvas_width=1440,
        canvas_height=1280,
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
    version_suffix = f" · {escape(model.version_label)}" if model.version_label else ""
    weak_foot_copy = f" · {escape(model.weak_foot_label)}" if model.weak_foot_label else ""
    habits_block = ""
    if model.habit_text:
        habits_block = f"""
        <section class="info-card">
            <h3>球员习惯</h3>
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
    <title>{escape(model.player_name)} - HEIGO 分享页</title>
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
            font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
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
        .info-row {{ display: grid; grid-template-columns: 96px 1fr; gap: 12px; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--line); }}
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
        .attr-row, .metric-row {{ display: grid; grid-template-columns: 88px 32px 1fr; gap: 10px; align-items: center; margin-bottom: 8px; }}
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
                <div><span class="eyebrow">HEIGO 球员详情图</span></div>
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
                        <h3>位置熟练度</h3>
                        <div class="chip-wrap">{_render_html_chips(model.position_chips, "暂无位置熟练度数据")}</div>
                    </section>
                    <section class="info-card">
                        <h3>顶级位置</h3>
                        <div class="chip-wrap">{_render_html_chips(model.top_position_chips, "暂无顶级位置数据")}</div>
                    </section>
                    {habits_block}
                </aside>
                <section>
                    <div class="main-grid">{attribute_groups}</div>
                    <div style="height:14px"></div>
                    <div class="main-grid" style="grid-template-columns: minmax(0, 1fr) 320px;">
                        {hidden_group}
                        <section class="metric-card">
                            <h3>能力雷达摘要</h3>
                            {_render_html_radar_metrics(model)}
                        </section>
                    </div>
                </section>
            </div>
        </section>
    </main>
</body>
</html>"""


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
            f'<text x="{x + 100}" y="{row_y}" font-size="13" font-weight="700" fill="{text_fill}" text-anchor="end">{int(round(item.value))}</text>'
            f'<rect x="{x + 114}" y="{row_y - 10}" width="{width - 132}" height="10" rx="5" fill="{line_fill}" />'
            f'<rect x="{x + 114}" y="{row_y - 10}" width="{((width - 132) * item.percent / 100):.1f}" height="10" rx="5" fill="{bar_fill}" />'
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
    version_suffix = f" · {model.version_label}" if model.version_label else ""
    preview_suffix = f" · {model.weak_foot_label}" if model.weak_foot_label else ""

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
    for chip in model.position_chips or (ShareChip("暂无", "位置数据"),):
        chip_width = max(70, 22 + len(chip.label) * 9 + len(chip.value) * 7)
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
    for chip in model.top_position_chips or (ShareChip("暂无", "顶级位置"),):
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
            ring_points.append(
                f"{radar_center_x + (point_x - radar_center_x) * scale:.1f},{radar_center_y + (point_y - radar_center_y) * scale:.1f}"
            )
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
            f'<text x="78" y="{block_y + 28}" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">球员习惯</text>'
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
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg-gradient)" />
  <rect x="30" y="28" width="{width - 60}" height="{height - 56}" rx="26" fill="{tokens["panel"]}" stroke="{tokens["line"]}" />
  <rect x="60" y="60" width="112" height="32" rx="16" fill="{tokens["accent_soft"]}" />
  <text x="116" y="81" font-size="12" font-weight="800" fill="{tokens["accent"]}" text-anchor="middle" letter-spacing="1.6">HEIGO 球员详情图</text>
  <text x="{width - 66}" y="82" font-size="13" font-weight="700" fill="{tokens["muted"]}" text-anchor="end">{escape(model.preview_label + preview_suffix + version_suffix)}</text>
  <rect x="60" y="118" width="360" height="{height - 178}" rx="22" fill="{tokens["panel_soft"]}" stroke="{tokens["line"]}" />
  <text x="78" y="166" font-size="42" font-weight="800" fill="{tokens["text"]}">{escape(model.player_name)}</text>
  <text x="78" y="194" font-size="13" fill="{tokens["muted"]}" letter-spacing="1.2">UID: {model.uid}{escape(version_suffix)}</text>
  {"".join(info_rows)}
  <text x="78" y="528" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">位置熟练度</text>
  {"".join(position_chips)}
  <text x="78" y="{top_chip_y - 18}" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">顶级位置</text>
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
  <text x="1024" y="614" font-size="14" font-weight="700" fill="{tokens["muted"]}" letter-spacing="1.5">能力雷达摘要</text>
  {"".join(radar_rows)}
  {"".join(grid_rings)}
  {"".join(radar_axes)}
  {"".join(radar_labels)}
  <polygon points="{radar_polygon}" fill="rgba(96,165,250,0.30)" stroke="#60a5fa" stroke-width="2" />
</svg>"""
