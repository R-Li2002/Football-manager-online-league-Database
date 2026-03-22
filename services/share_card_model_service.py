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
    ("reflexes", "Reflexes"),
    ("aerial_ability", "Aerial"),
    ("kicking", "Kicking"),
    ("handling", "Handling"),
    ("command_of_area", "Command"),
    ("throwing", "Throwing"),
    ("one_on_ones", "1v1"),
    ("communication", "Comms"),
    ("tendency_to_punch", "Punching"),
    ("rushing_out", "Rush Out"),
    ("eccentricity", "Eccentric"),
]
OUTFIELD_TECHNICAL_FIELDS = [
    ("passing", "Passing"),
    ("crossing", "Crossing"),
    ("marking", "Marking"),
    ("technique", "Technique"),
    ("dribbling", "Dribbling"),
    ("tackling", "Tackling"),
    ("finishing", "Finishing"),
    ("first_touch", "First Touch"),
    ("heading", "Heading"),
    ("long_shots", "Long Shots"),
]
SET_PIECE_FIELDS = [
    ("penalty", "Penalty"),
    ("corner", "Corner"),
    ("long_throws", "Long Throws"),
    ("free_kick", "Free Kick"),
]
MENTAL_FIELDS = [
    ("flair", "Flair"),
    ("positioning", "Positioning"),
    ("work_rate", "Work Rate"),
    ("concentration", "Concentration"),
    ("decisions", "Decisions"),
    ("leadership", "Leadership"),
    ("aggression", "Aggression"),
    ("vision", "Vision"),
    ("teamwork", "Teamwork"),
    ("off_the_ball", "Off Ball"),
    ("determination", "Determination"),
    ("bravery", "Bravery"),
    ("anticipation", "Anticipation"),
    ("composure", "Composure"),
]
PHYSICAL_FIELDS = [
    ("acceleration", "Acceleration"),
    ("jumping", "Jumping"),
    ("agility", "Agility"),
    ("stamina", "Stamina"),
    ("balance", "Balance"),
    ("strength", "Strength"),
    ("pace", "Pace"),
    ("natural_fitness", "Natural Fit"),
]
HIDDEN_FIELDS = [
    ("consistency", "Consistency"),
    ("adaptability", "Adaptability"),
    ("pressure", "Pressure"),
    ("ambition", "Ambition"),
    ("professionalism", "Professionalism"),
    ("important_matches", "Big Matches"),
    ("injury_proneness", "Injury"),
    ("versatility", "Versatility"),
    ("sportsmanship", "Sportsmanship"),
    ("temperament", "Temperament"),
    ("loyalty", "Loyalty"),
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
    return ("Left Foot", min(20, left + 1)) if left < right else ("Right Foot", min(20, right + 1))


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
        if foot_label == "Left Foot":
            payload["left_foot"] = foot_value
        else:
            payload["right_foot"] = foot_value

    payload["preview_step"] = preview_step
    payload["preview_ca"] = int(player.ca or 0) + _preview_ca_gain(preview_step)
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
            ("Shot Stop", _average_values([preview_player.get("one_on_ones"), preview_player.get("reflexes")])) ,
            ("Physical", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])) ,
            ("Speed", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])) ,
            ("Mental", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])) ,
            ("Command", _average_values([preview_player.get("command_of_area"), preview_player.get("communication")])) ,
            ("Eccentric", float(preview_player.get("eccentricity") or 0)),
            ("Aerial", _average_values([preview_player.get("aerial_ability"), preview_player.get("handling")])) ,
            ("Kicking", _average_values([preview_player.get("kicking"), preview_player.get("throwing")])) ,
        ]
    return [
        ("Defense", _average_values([preview_player.get("marking"), preview_player.get("tackling"), preview_player.get("positioning")])) ,
        ("Physical", _average_values([preview_player.get("agility"), preview_player.get("balance"), preview_player.get("stamina"), preview_player.get("strength")])) ,
        ("Speed", _average_values([preview_player.get("acceleration"), preview_player.get("pace")])) ,
        ("Creation", _average_values([preview_player.get("passing"), preview_player.get("flair"), preview_player.get("vision")])) ,
        ("Attack", _average_values([preview_player.get("finishing"), preview_player.get("composure"), preview_player.get("off_the_ball")])) ,
        ("Technique", _average_values([preview_player.get("dribbling"), preview_player.get("first_touch"), preview_player.get("technique")])) ,
        ("Aerial", _average_values([preview_player.get("heading"), preview_player.get("jumping")])) ,
        ("Mental", _average_values([preview_player.get("anticipation"), preview_player.get("bravery"), preview_player.get("concentration"), preview_player.get("decisions"), preview_player.get("determination"), preview_player.get("teamwork")])) ,
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


def _build_top_position_chips(player: PlayerAttributeDetailResponse) -> tuple[ShareChip, ...]:
    return tuple(ShareChip(label=item.position, value=str(int(item.score))) for item in player.top_positions)


def _build_info_rows(player: PlayerAttributeDetailResponse, preview_player: dict) -> tuple[ShareInfoRow, ...]:
    return (
        ShareInfoRow("Nationality", player.nationality or "-"),
        ShareInfoRow("Age", str(player.age or "-")),
        ShareInfoRow("Birth", player.birth_date or "Unknown"),
        ShareInfoRow("Position", player.position or "-"),
        ShareInfoRow("CA / PA", f"{int(preview_player.get('preview_ca') or player.ca or 0)} / {int(player.pa or 0)}"),
        ShareInfoRow("Left / Right", f"{preview_player.get('left_foot', '-')} / {preview_player.get('right_foot', '-')}"),
        ShareInfoRow("Height", _format_height(player.height)),
        ShareInfoRow("HEIGO Club", player.heigo_club or "-"),
        ShareInfoRow("Club", player.club or "-"),
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
        preview_label=f"Growth Preview +{_clamp_growth_preview_step(step)}" if _clamp_growth_preview_step(step) > 0 else "Current Attributes",
        weak_foot_label=weak_foot_label,
        theme=_normalize_theme(theme),
        is_goalkeeper=is_goalkeeper,
        info_rows=_build_info_rows(player, preview_player),
        position_chips=_build_position_chips(preview_player),
        top_position_chips=_build_top_position_chips(player),
        attribute_groups=(
            _build_share_group("Technical", technical_fields, preview_player),
            _build_share_group("Mental", MENTAL_FIELDS, preview_player),
            _build_share_group("Physical", PHYSICAL_FIELDS, preview_player),
            _build_share_group("Hidden", HIDDEN_FIELDS, preview_player),
        ),
        radar_metrics=radar_metrics,
        habit_text=(player.player_habits or "").strip(),
        canvas_width=1440,
        canvas_height=1280,
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
    page_size: int = 16,
    theme: str = "dark",
) -> RosterShareCardModel:
    normalized_page_size = max(8, min(24, int(page_size or 16)))
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
