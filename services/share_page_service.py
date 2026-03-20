from __future__ import annotations

from html import escape
from typing import Iterable

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


def _average_values(values: Iterable[int | float | None]) -> float:
    normalized = [float(item) for item in values if float(item or 0) > 0]
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


def _bar_width(value: int | float | None) -> int:
    return max(0, min(100, int(round((float(value or 0) / 20) * 100))))


def _render_attribute_group(title: str, fields: list[tuple[str, str]], preview_player: dict) -> str:
    rows = []
    for key, label in fields:
        value = int(preview_player.get(key) or 0)
        rows.append(
            f"""
            <div class="attr-row">
                <span class="attr-label">{escape(label)}</span>
                <span class="attr-value">{value}</span>
                <span class="attr-bar"><span class="attr-bar-fill" style="width:{_bar_width(value)}%"></span></span>
            </div>
            """
        )
    return f'<section class="group-card"><h3>{escape(title)}</h3>{"".join(rows)}</section>'


def _render_position_chips(preview_player: dict) -> str:
    chips = []
    for key, label in POSITION_FIELDS:
        value = int(preview_player.get(key) or 0)
        if value <= 1:
            continue
        chips.append(f'<span class="chip"><strong>{escape(label)}</strong> {value}</span>')
    if not chips:
        return '<div class="muted">暂无位置熟练度数据</div>'
    return "".join(chips)


def _render_top_positions(player: PlayerAttributeDetailResponse) -> str:
    if not player.top_positions:
        return '<div class="muted">暂无顶级位置数据</div>'
    return "".join(
        f'<span class="chip"><strong>{escape(item.position)}</strong> {int(item.score)}</span>'
        for item in player.top_positions
    )


def _render_radar_metrics(preview_player: dict) -> str:
    rows = []
    for label, value in _build_radar_metrics(preview_player):
        rows.append(
            f"""
            <div class="metric-row">
                <span class="metric-label">{escape(label)}</span>
                <span class="metric-value">{value:.1f}</span>
                <span class="attr-bar"><span class="attr-bar-fill metric-fill" style="width:{_bar_width(value)}%"></span></span>
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
    preview_player = build_preview_player(player, step)
    is_goalkeeper = int(preview_player.get("pos_gk") or 0) >= 15
    technical_fields = GOALKEEPER_TECHNICAL_FIELDS if is_goalkeeper else OUTFIELD_TECHNICAL_FIELDS + SET_PIECE_FIELDS
    title_suffix = f" · {escape(version)}" if version else ""
    preview_badge = (
        f"成长预览 +{step}"
        if step > 0
        else "当前属性"
    )
    weak_foot = preview_player.get("preview_weak_foot")
    weak_foot_copy = (
        f" · {escape(weak_foot[0])}逆足 +1"
        if weak_foot
        else ""
    )
    ca_copy = f"{int(preview_player.get('preview_ca') or player.ca)} / {int(player.pa)}"
    theme_class = "theme-light" if theme == "light" else "theme-dark"

    habits_block = ""
    if player.player_habits:
        habits_block = f"""
        <section class="info-card">
            <h3>球员习惯</h3>
            <p class="habit-copy">{escape(player.player_habits)}</p>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(player.name)} - HEIGO 分享页</title>
    <style>
        :root {{
            color-scheme: dark;
            --bg: #0b1220;
            --panel: rgba(15, 23, 42, 0.92);
            --panel-soft: rgba(30, 41, 59, 0.82);
            --line: rgba(148, 163, 184, 0.18);
            --text: #ecf3ff;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent-2: #22c55e;
        }}
        body.theme-light {{
            color-scheme: light;
            --bg: #eef4fb;
            --panel: rgba(255, 255, 255, 0.96);
            --panel-soft: rgba(247, 250, 253, 0.98);
            --line: rgba(100, 116, 139, 0.16);
            --text: #172033;
            --muted: #5f6c84;
            --accent: #2563eb;
            --accent-2: #16a34a;
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
        .page {{
            width: 1320px;
            margin: 0 auto;
            padding: 28px;
        }}
        .card {{
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
        }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: center;
            margin-bottom: 18px;
        }}
        .eyebrow {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            background: rgba(56, 189, 248, 0.14);
            color: var(--accent);
        }}
        .preview {{
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
        }}
        .layout {{
            display: grid;
            grid-template-columns: 340px minmax(0, 1fr);
            gap: 16px;
        }}
        .info-card, .group-card, .metric-card {{
            border: 1px solid var(--line);
            background: var(--panel-soft);
            border-radius: 18px;
            padding: 16px;
        }}
        .identity h1 {{
            margin: 0 0 8px;
            font-size: 40px;
            line-height: 1;
        }}
        .uid {{
            color: var(--muted);
            font-size: 13px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .info-list {{
            display: grid;
            gap: 8px;
            margin-top: 16px;
        }}
        .info-row {{
            display: grid;
            grid-template-columns: 96px 1fr;
            gap: 12px;
            align-items: center;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--line);
        }}
        .info-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .label {{ color: var(--muted); font-size: 13px; }}
        .value {{ text-align: right; font-weight: 700; }}
        .chip-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
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
        .main-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
        }}
        .group-card h3, .info-card h3, .metric-card h3 {{
            margin: 0 0 12px;
            font-size: 13px;
            color: var(--muted);
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .attr-row, .metric-row {{
            display: grid;
            grid-template-columns: 88px 32px 1fr;
            gap: 10px;
            align-items: center;
            margin-bottom: 8px;
        }}
        .attr-row:last-child, .metric-row:last-child {{ margin-bottom: 0; }}
        .attr-label, .metric-label {{ font-size: 13px; }}
        .attr-value, .metric-value {{ text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }}
        .attr-bar {{
            height: 10px;
            background: rgba(148, 163, 184, 0.14);
            border-radius: 999px;
            overflow: hidden;
        }}
        .attr-bar-fill {{
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
        }}
        .metric-fill {{
            background: linear-gradient(90deg, #60a5fa, #22d3ee);
        }}
        .muted {{
            color: var(--muted);
            font-size: 13px;
        }}
        .habit-copy {{
            margin: 0;
            line-height: 1.6;
            color: var(--text);
        }}
    </style>
</head>
<body class="{theme_class}">
    <main class="page">
        <section class="card">
            <div class="topbar">
                <div>
                    <span class="eyebrow">HEIGO 球员详情图</span>
                </div>
                <div class="preview">{escape(preview_badge)}{weak_foot_copy}{title_suffix}</div>
            </div>
            <div class="layout">
                <aside>
                    <section class="info-card identity">
                        <h1>{escape(player.name)}</h1>
                        <div class="uid">UID: {player.uid}{title_suffix}</div>
                        <div class="info-list">
                            <div class="info-row"><span class="label">国籍</span><span class="value">{escape(player.nationality or "-")}</span></div>
                            <div class="info-row"><span class="label">年龄</span><span class="value">{player.age}</span></div>
                            <div class="info-row"><span class="label">生日</span><span class="value">{escape(player.birth_date or "未知")}</span></div>
                            <div class="info-row"><span class="label">位置</span><span class="value">{escape(player.position or "-")}</span></div>
                            <div class="info-row"><span class="label">CA / PA</span><span class="value">{ca_copy}</span></div>
                            <div class="info-row"><span class="label">左脚 / 右脚</span><span class="value">{preview_player.get("left_foot", "-")} / {preview_player.get("right_foot", "-")}</span></div>
                            <div class="info-row"><span class="label">身高</span><span class="value">{player.height} cm</span></div>
                            <div class="info-row"><span class="label">HEIGO俱乐部</span><span class="value">{escape(player.heigo_club or "-")}</span></div>
                            <div class="info-row"><span class="label">现实俱乐部</span><span class="value">{escape(player.club or "-")}</span></div>
                        </div>
                    </section>
                    <section class="info-card">
                        <h3>位置熟练度</h3>
                        <div class="chip-wrap">{_render_position_chips(preview_player)}</div>
                    </section>
                    <section class="info-card">
                        <h3>顶级位置</h3>
                        <div class="chip-wrap">{_render_top_positions(player)}</div>
                    </section>
                    {habits_block}
                </aside>
                <section>
                    <div class="main-grid">
                        {_render_attribute_group("技术", technical_fields, preview_player)}
                        {_render_attribute_group("精神", MENTAL_FIELDS, preview_player)}
                        {_render_attribute_group("身体", PHYSICAL_FIELDS, preview_player)}
                    </div>
                    <div style="height:14px"></div>
                    <div class="main-grid" style="grid-template-columns: minmax(0, 1fr) 320px;">
                        {_render_attribute_group("隐藏", HIDDEN_FIELDS, preview_player)}
                        <section class="metric-card">
                            <h3>能力雷达摘要</h3>
                            {_render_radar_metrics(preview_player)}
                        </section>
                    </div>
                </section>
            </div>
        </section>
    </main>
</body>
</html>"""
