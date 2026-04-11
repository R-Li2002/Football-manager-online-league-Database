from __future__ import annotations

from typing import Any

from schemas_read import (
    AttributeSearchResponse,
    PlayerAttributeDetailResponse,
    PlayerRadarMetricResponse,
    PlayerReactionLeaderboardItemResponse,
    PlayerResponse,
    PositionScoreResponse,
    TeamInfoResponse,
    TeamResponse,
)

TEAM_RESPONSE_FIELDS = (
    "id",
    "name",
    "manager",
    "level",
    "wage",
    "team_size",
    "gk_count",
    "final_wage",
    "count_8m",
    "count_7m",
    "count_fake",
    "notes",
)

ATTRIBUTE_DETAIL_FIELDS = (
    "uid",
    "name",
    "position",
    "age",
    "ca",
    "pa",
    "nationality",
    "club",
    "height",
    "weight",
    "left_foot",
    "right_foot",
    "radar_defense",
    "radar_physical",
    "radar_speed",
    "radar_creativity",
    "radar_attack",
    "radar_technical",
    "radar_aerial",
    "radar_mental",
    "birth_date",
    "national_caps",
    "national_goals",
    "player_habits",
    "player_habits_raw_code",
    "player_habits_high_bits",
    "corner",
    "crossing",
    "dribbling",
    "finishing",
    "first_touch",
    "free_kick",
    "heading",
    "long_shots",
    "long_throws",
    "marking",
    "passing",
    "penalty",
    "tackling",
    "technique",
    "aggression",
    "anticipation",
    "bravery",
    "composure",
    "concentration",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "off_the_ball",
    "positioning",
    "teamwork",
    "vision",
    "work_rate",
    "acceleration",
    "agility",
    "balance",
    "jumping",
    "natural_fitness",
    "pace",
    "stamina",
    "strength",
    "consistency",
    "dirtiness",
    "important_matches",
    "injury_proneness",
    "versatility",
    "adaptability",
    "ambition",
    "controversy",
    "loyalty",
    "pressure",
    "professionalism",
    "sportsmanship",
    "temperament",
    "aerial_ability",
    "command_of_area",
    "communication",
    "eccentricity",
    "handling",
    "kicking",
    "one_on_ones",
    "reflexes",
    "rushing_out",
    "tendency_to_punch",
    "throwing",
    "pos_gk",
    "pos_dl",
    "pos_dc",
    "pos_dr",
    "pos_wbl",
    "pos_wbr",
    "pos_dm",
    "pos_ml",
    "pos_mc",
    "pos_mr",
    "pos_aml",
    "pos_amc",
    "pos_amr",
    "pos_st",
)

POSITION_SCORE_FIELDS = (
    ("GK", "pos_gk"),
    ("DL", "pos_dl"),
    ("DC", "pos_dc"),
    ("DR", "pos_dr"),
    ("WBL", "pos_wbl"),
    ("WBR", "pos_wbr"),
    ("DM", "pos_dm"),
    ("ML", "pos_ml"),
    ("MC", "pos_mc"),
    ("MR", "pos_mr"),
    ("AML", "pos_aml"),
    ("AMC", "pos_amc"),
    ("AMR", "pos_amr"),
    ("ST", "pos_st"),
)

GOALKEEPER_RADAR_FIELDS = (
    ("拦截射门", "radar_gk_shot_stopping"),
    ("身体", "radar_gk_physical"),
    ("速度", "radar_gk_speed"),
    ("精神", "radar_gk_mental"),
    ("指挥防守", "radar_gk_command"),
    ("意外性", "radar_gk_eccentricity"),
    ("制空", "radar_gk_aerial"),
    ("大脚", "radar_gk_kicking"),
)

OUTFIELD_RADAR_FIELDS = (
    ("防守", "radar_defense"),
    ("身体", "radar_physical"),
    ("速度", "radar_speed"),
    ("创造", "radar_creativity"),
    ("进攻", "radar_attack"),
    ("技术", "radar_technical"),
    ("制空", "radar_aerial"),
    ("精神", "radar_mental"),
)


def build_team_response(team: Any, overlay: dict[str, Any], stat_sources) -> TeamResponse:
    payload = {field_name: getattr(team, field_name) for field_name in TEAM_RESPONSE_FIELDS}
    payload.update(
        total_value=overlay.get("total_value", team.total_value),
        avg_value=overlay.get("avg_value", team.avg_value),
        avg_ca=overlay.get("avg_ca", team.avg_ca),
        avg_pa=overlay.get("avg_pa", team.avg_pa),
        total_growth=overlay.get("total_growth", team.total_growth),
        stat_sources=stat_sources,
    )
    return TeamResponse(**payload)


def build_player_response(player: Any, nationality: str) -> PlayerResponse:
    return PlayerResponse(
        uid=player.uid,
        name=player.name,
        age=player.age,
        initial_ca=player.initial_ca,
        ca=player.ca,
        pa=player.pa,
        position=player.position,
        nationality=nationality,
        team_name=player.team_name,
        wage=player.wage,
        slot_type=player.slot_type or "",
    )


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(value)


def build_attribute_search_response(player: Any, *, data_version: str, heigo_club: str) -> AttributeSearchResponse:
    return AttributeSearchResponse(
        uid=player.uid,
        name=player.name,
        data_version=getattr(player, "data_version", data_version),
        position=player.position,
        age=player.age,
        ca=_coerce_int(player.ca),
        pa=_coerce_int(player.pa),
        nationality=player.nationality,
        club=player.club,
        heigo_club=heigo_club,
    )


def _build_top_positions(attr: Any) -> list[PositionScoreResponse]:
    scored_positions = [
        (position, getattr(attr, field_name))
        for position, field_name in POSITION_SCORE_FIELDS
        if (getattr(attr, field_name) or 0) > 0
    ]
    return [
        PositionScoreResponse(position=position, score=score)
        for position, score in sorted(scored_positions, key=lambda item: item[1], reverse=True)[:6]
    ]


def _build_radar_profile(attr: Any) -> list[PlayerRadarMetricResponse]:
    radar_fields = GOALKEEPER_RADAR_FIELDS if (getattr(attr, "pos_gk", 0) or 0) >= 15 else OUTFIELD_RADAR_FIELDS
    return [
        PlayerRadarMetricResponse(label=label, value=getattr(attr, field_name))
        for label, field_name in radar_fields
    ]


def build_player_attribute_detail_response(
    attr: Any,
    *,
    data_version: str,
    heigo_club: str,
    reaction_summary,
) -> PlayerAttributeDetailResponse:
    payload = {field_name: getattr(attr, field_name) for field_name in ATTRIBUTE_DETAIL_FIELDS}
    payload["ca"] = _coerce_int(payload.get("ca"))
    payload["pa"] = _coerce_int(payload.get("pa"))
    payload.update(
        data_version=getattr(attr, "data_version", data_version),
        heigo_club=heigo_club,
        top_positions=_build_top_positions(attr),
        radar_profile=_build_radar_profile(attr),
        reaction_summary=reaction_summary,
    )
    return PlayerAttributeDetailResponse(**payload)


def build_player_reaction_leaderboard_item_response(
    row: Any,
    *,
    data_version: str,
    fallback_team: str,
) -> PlayerReactionLeaderboardItemResponse:
    return PlayerReactionLeaderboardItemResponse(
        uid=row.uid,
        name=row.name,
        data_version=data_version,
        position=row.position,
        age=row.age,
        ca=_coerce_int(row.ca),
        pa=_coerce_int(row.pa),
        heigo_club=row.heigo_club or fallback_team,
        flowers=row.flowers,
        eggs=row.eggs,
        net_score=row.net_score,
        total_reactions=row.total_reactions,
        updated_at=row.updated_at,
    )


def build_team_info_response(team: Any) -> TeamInfoResponse:
    return TeamInfoResponse(
        id=team.id,
        name=team.name,
        manager=team.manager,
        level=team.level,
        wage=team.wage,
        notes=team.notes,
    )
