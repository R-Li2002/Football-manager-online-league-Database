from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from domain_types import SLOT_TYPE_7M, SLOT_TYPE_8M, SLOT_TYPE_FAKE, normalize_slot_type
from schemas_read import PlayerAttributeDetailResponse, PlayerResponse, TeamInfoResponse, WageDetailResponse


SHARE_FONT_FAMILY = (
    '"Noto Sans CJK SC", "Noto Sans SC", "PingFang SC", '
    '"Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif'
)

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

POSITION_MARKERS = [
    ("pos_st", "ST", 50.0, 12.0),
    ("pos_aml", "AML", 10.5, 24.0),
    ("pos_amc", "AMC", 50.0, 24.0),
    ("pos_amr", "AMR", 89.5, 24.0),
    ("pos_ml", "ML", 10.5, 42.0),
    ("pos_mc", "MC", 50.0, 42.0),
    ("pos_mr", "MR", 89.5, 42.0),
    ("pos_dm", "DM", 50.0, 62.0),
    ("pos_wbl", "WBL", 10.5, 62.0),
    ("pos_wbr", "WBR", 89.5, 62.0),
    ("pos_dl", "DL", 10.5, 82.0),
    ("pos_dc", "DC", 50.0, 82.0),
    ("pos_dr", "DR", 89.5, 82.0),
    ("pos_gk", "GK", 50.0, 94.0),
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
class SharePositionMarker:
    key: str
    label: str
    score: int
    x_percent: float
    y_percent: float


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
    reaction_flower_count: int
    reaction_egg_count: int
    position_markers: tuple[SharePositionMarker, ...]
    position_chips: tuple[ShareChip, ...]
    top_position_chips: tuple[ShareChip, ...]
    attribute_groups: tuple[ShareGroup, ...]
    radar_metrics: tuple[ShareMetric, ...]
    habit_text: str
    canvas_width: int
    canvas_height: int


@dataclass(frozen=True)
class WageShareCardModel:
    player_name: str
    uid: int
    team_name: str
    position: str
    age_label: str
    slot_type_label: str
    theme: str
    headline_value: str
    summary_rows: tuple[ShareInfoRow, ...]
    formula_rows: tuple[ShareInfoRow, ...]
    canvas_width: int
    canvas_height: int


@dataclass(frozen=True)
class RosterPlayerRow:
    index: int
    name: str
    position: str
    age_label: str
    ca_pa_label: str
    wage_label: str
    slot_type_label: str


@dataclass(frozen=True)
class RosterShareCardModel:
    team_name: str
    manager_name: str
    level_label: str
    theme: str
    summary_rows: tuple[ShareInfoRow, ...]
    player_rows: tuple[RosterPlayerRow, ...]
    page: int
    total_pages: int
    total_players: int
    canvas_width: int
    canvas_height: int


def _normalize_theme(theme: str | None) -> str:
    return "light" if theme == "light" else "dark"


def _clamp_attribute_value(value: int | float | None) -> int:
    return max(1, min(20, int(value or 0)))


def _clamp_growth_preview_step(step: int | None) -> int:
    return max(0, min(5, int(step or 0)))


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
    payload["preview_weak_foot"] = weak_foot
    return payload


def _average_values(values: list[int | float | None]) -> float:
    normalized = [float(value or 0) for value in values if float(value or 0) > 0]
    if not normalized:
        return 0.0
    return round(sum(normalized) / len(normalized), 1)


def _build_radar_metrics(preview_player: dict) -> list[tuple[str, float]]:
    is_goalkeeper = int(preview_player.get("pos_gk") or 0) >= 15
    if is_goalkeeper:
        return [
            ("拦截射门", _average_values([preview_player.get("one_on_ones"), preview_player.get("reflexes")])) ,
            ("身体", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])) ,
            ("速度", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])) ,
            ("精神", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])) ,
            ("指挥防守", _average_values([preview_player.get("command_of_area"), preview_player.get("communication")])) ,
            ("意外性", float(preview_player.get("eccentricity") or 0)),
            ("制空", _average_values([preview_player.get("aerial_ability"), preview_player.get("handling")])) ,
            ("大脚", _average_values([preview_player.get("kicking"), preview_player.get("throwing")])) ,
        ]
    return [
        ("防守", _average_values([preview_player.get("marking"), preview_player.get("tackling"), preview_player.get("positioning")])) ,
        ("身体", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])) ,
        ("速度", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])) ,
        ("创造", _average_values([preview_player.get("passing"), preview_player.get("flair"), preview_player.get("vision")])) ,
        ("进攻", _average_values([preview_player.get("finishing"), preview_player.get("composure"), preview_player.get("off_the_ball")])) ,
        ("技术", _average_values([preview_player.get("dribbling"), preview_player.get("first_touch"), preview_player.get("technique")])) ,
        ("制空", _average_values([preview_player.get("heading"), preview_player.get("jumping")])) ,
        ("精神", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])) ,
    ]


def _metric_percent(value: int | float) -> float:
    return max(0.0, min(100.0, round((float(value or 0) / 20.0) * 100.0, 1)))


def _build_share_group(title: str, fields: list[tuple[str, str]], preview_player: dict) -> ShareGroup:
    return ShareGroup(
        title=title,
        items=tuple(
            ShareMetric(
                key=key,
                label=label,
                value=float(int(preview_player.get(key) or 0)),
                percent=_metric_percent(int(preview_player.get(key) or 0)),
            )
            for key, label in fields
        ),
    )


def _format_height(value: int | None) -> str:
    return f"{int(value)} cm" if value else "-"


def _format_money(value: int | float | None) -> str:
    return f"{float(value or 0):.3f}M"


def _format_decimal(value: int | float | None) -> str:
    return f"{float(value or 0):.2f}"


def _build_position_chips(preview_player: dict) -> tuple[ShareChip, ...]:
    chips: list[ShareChip] = []
    for key, label in POSITION_FIELDS:
        value = int(preview_player.get(key) or 0)
        if value <= 1:
            continue
        chips.append(ShareChip(label=label, value=str(value)))
    return tuple(chips)


def _build_position_markers(preview_player: dict) -> tuple[SharePositionMarker, ...]:
    markers: list[SharePositionMarker] = []
    for key, label, x_percent, y_percent in POSITION_MARKERS:
        score = int(preview_player.get(key) or 0)
        if score <= 1:
            continue
        markers.append(
            SharePositionMarker(
                key=key,
                label=label,
                score=score,
                x_percent=x_percent,
                y_percent=y_percent,
            )
        )
    return tuple(markers)


def _build_top_position_chips(player: PlayerAttributeDetailResponse) -> tuple[ShareChip, ...]:
    return tuple(ShareChip(label=item.position, value=str(int(item.score))) for item in player.top_positions)


def _build_info_rows(player: PlayerAttributeDetailResponse, preview_player: dict) -> tuple[ShareInfoRow, ...]:
    return (
        ShareInfoRow("国籍", player.nationality or "-"),
        ShareInfoRow("年龄", str(player.age or "-")),
        ShareInfoRow("生日", player.birth_date or "未知"),
        ShareInfoRow("位置", player.position or "-"),
        ShareInfoRow("CA / PA", f"{int(player.ca or 0)} / {int(player.pa or 0)}"),
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
    weak_foot_label = f"{weak_foot[0]} +1" if weak_foot else ""
    radar_metrics = tuple(
        ShareMetric(
            key=f"radar_{index}",
            label=label,
            value=value,
            percent=_metric_percent(value),
        )
        for index, (label, value) in enumerate(_build_radar_metrics(preview_player))
    )
    return ShareCardModel(
        player_name=player.name,
        uid=player.uid,
        version_label=version or player.data_version or "",
        preview_label=f"成长预览 +{_clamp_growth_preview_step(step)}" if _clamp_growth_preview_step(step) > 0 else "当前属性",
        weak_foot_label=weak_foot_label,
        theme=_normalize_theme(theme),
        is_goalkeeper=is_goalkeeper,
        info_rows=_build_info_rows(player, preview_player),
        reaction_flower_count=0,
        reaction_egg_count=0,
        position_markers=_build_position_markers(preview_player),
        position_chips=_build_position_chips(preview_player),
        top_position_chips=_build_top_position_chips(player),
        attribute_groups=(
            _build_share_group("门将属性" if is_goalkeeper else "技术", technical_fields, preview_player),
            _build_share_group("精神", MENTAL_FIELDS, preview_player),
            _build_share_group("身体", PHYSICAL_FIELDS, preview_player),
            _build_share_group("隐藏", HIDDEN_FIELDS, preview_player),
        ),
        radar_metrics=radar_metrics,
        habit_text=(player.player_habits or "").strip(),
        canvas_width=1440,
        canvas_height=1024,
    )


def build_wage_share_card_model(
    player: PlayerAttributeDetailResponse,
    wage_detail: WageDetailResponse,
    *,
    theme: str = "dark",
) -> WageShareCardModel:
    slot_type = normalize_slot_type(wage_detail.slot_type) or "Normal"
    return WageShareCardModel(
        player_name=player.name,
        uid=player.uid,
        team_name=player.heigo_club or "-",
        position=player.position or "-",
        age_label=str(player.age or "-"),
        slot_type_label=slot_type,
        theme=_normalize_theme(theme),
        headline_value=_format_money(wage_detail.wage),
        summary_rows=(
            ShareInfoRow("Club", player.heigo_club or "-"),
            ShareInfoRow("Position", player.position or "-"),
            ShareInfoRow("Age", str(player.age or "-")),
            ShareInfoRow("CA / PA", f"{int(player.ca or 0)} / {int(player.pa or 0)}"),
            ShareInfoRow("Slot", slot_type),
            ShareInfoRow("Version", player.data_version or "-"),
        ),
        formula_rows=(
            ShareInfoRow("Initial Value", _format_decimal(wage_detail.initial_value)),
            ShareInfoRow("Current Value", _format_decimal(wage_detail.current_value)),
            ShareInfoRow("Potential Value", _format_decimal(wage_detail.potential_value)),
            ShareInfoRow("Final Value", _format_decimal(wage_detail.final_value)),
            ShareInfoRow("Initial Field", _format_decimal(wage_detail.initial_field)),
            ShareInfoRow("Coefficient", _format_decimal(wage_detail.coefficient)),
            ShareInfoRow("Wage", _format_money(wage_detail.wage)),
        ),
        canvas_width=1440,
        canvas_height=900,
    )


def _build_roster_summary_rows(team_name: str, players: list[PlayerResponse], team_info: TeamInfoResponse | None) -> tuple[ShareInfoRow, ...]:
    total_players = len(players)
    avg_ca = round(sum(float(player.ca or 0) for player in players) / total_players, 1) if total_players else 0.0
    avg_pa = round(sum(float(player.pa or 0) for player in players) / total_players, 1) if total_players else 0.0
    avg_wage = round(sum(float(player.wage or 0) for player in players) / total_players, 3) if total_players else 0.0
    slot_types = [normalize_slot_type(player.slot_type) for player in players]
    return (
        ShareInfoRow("Manager", team_info.manager if team_info and team_info.manager else "-"),
        ShareInfoRow("Level", team_info.level if team_info and team_info.level else "-"),
        ShareInfoRow("Players", str(total_players)),
        ShareInfoRow("Goalkeepers", str(sum("GK" in (player.position or "") for player in players))),
        ShareInfoRow("Avg CA", f"{avg_ca:.1f}"),
        ShareInfoRow("Avg PA", f"{avg_pa:.1f}"),
        ShareInfoRow("Avg Wage", _format_money(avg_wage)),
        ShareInfoRow("8M / 7M / Fake", f"{sum(item == SLOT_TYPE_8M for item in slot_types)} / {sum(item == SLOT_TYPE_7M for item in slot_types)} / {sum(item == SLOT_TYPE_FAKE for item in slot_types)}"),
        ShareInfoRow("Team", team_info.name if team_info else team_name),
    )


def build_roster_share_card_model(
    team_name: str,
    players: list[PlayerResponse],
    *,
    team_info: TeamInfoResponse | None = None,
    page: int = 1,
    page_size: int = 20,
    theme: str = "dark",
) -> RosterShareCardModel:
    normalized_page_size = max(20, min(20, int(page_size or 20)))
    total_players = len(players)
    total_pages = max(1, int(ceil(total_players / normalized_page_size))) if total_players else 1
    normalized_page = max(1, min(total_pages, int(page or 1)))
    start = (normalized_page - 1) * normalized_page_size
    sliced_players = players[start : start + normalized_page_size]
    player_rows = tuple(
        RosterPlayerRow(
            index=start + index + 1,
            name=player.name,
            position=player.position or "-",
            age_label=str(player.age or "-"),
            ca_pa_label=f"{int(player.ca or 0)} / {int(player.pa or 0)}",
            wage_label=_format_money(player.wage),
            slot_type_label=normalize_slot_type(player.slot_type) or "-",
        )
        for index, player in enumerate(sliced_players)
    )
    return RosterShareCardModel(
        team_name=team_info.name if team_info else team_name,
        manager_name=team_info.manager if team_info and team_info.manager else "-",
        level_label=team_info.level if team_info and team_info.level else "-",
        theme=_normalize_theme(theme),
        summary_rows=_build_roster_summary_rows(team_name, players, team_info),
        player_rows=player_rows,
        page=normalized_page,
        total_pages=total_pages,
        total_players=total_players,
        canvas_width=1440,
        canvas_height=1180,
    )
