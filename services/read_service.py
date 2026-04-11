from fastapi import HTTPException
from sqlalchemy.orm import Session

from repositories.attribute_repository import (
    ATTRIBUTE_RANGE_FIELD_ALLOWLIST,
    POSITION_SCORE_FIELD_ALLOWLIST,
    AttributeRangeFilter,
    PositionScoreFilter,
    get_attribute_model_for_versions,
    get_default_attribute_version,
    get_player_attribute_by_uid,
    list_available_attribute_versions,
    map_attribute_uid_to_primary_nationality,
    resolve_attribute_version,
    search_player_attributes_advanced,
    search_player_attributes_by_name,
)
from repositories.league_info_repository import list_league_info
from repositories.player_reaction_repository import list_player_reaction_leaderboard_rows
from repositories.player_repository import (
    get_player_by_uid,
    get_players_by_team_name,
    list_players_excluding_team,
    map_player_uid_to_team_name,
    search_players_by_name,
)
from repositories.team_repository import get_team_by_name, list_visible_teams
from schemas_read import (
    AdvancedAttributeSearchResponse,
    AttributeSearchResponse,
    AttributeVersionsResponse,
    PlayerAttributeDetailResponse,
    PlayerReactionLeaderboardResponse,
    PlayerResponse,
    TeamInfoResponse,
    TeamResponse,
    WageDetailResponse,
)
from schemas_write import AdvancedAttributeRangeRequest, AdvancedAttributeSearchRequest
from services.league_service import calculate_player_wage_payload
from services.read_presenters import (
    build_attribute_search_response,
    build_player_attribute_detail_response,
    build_player_reaction_leaderboard_item_response,
    build_player_response,
    build_team_info_response,
    build_team_response,
)
from services.reaction_service import build_player_reaction_summary
from services.team_stat_source_service import build_team_stat_sources, load_team_stat_overlays

LEVEL_ORDER = {"超级": 1, "甲级": 2, "乙级": 3}
VISIBLE_LEVEL = "隐藏"
SEA_TEAM_NAME = "85大海"
ATTRIBUTE_FALLBACK_TEAM = "大海"
ADVANCED_SEARCH_FIELD_LABELS = {
    "age": "年龄",
    "ca": "CA",
    "pa": "PA",
    "corner": "角球",
    "crossing": "传中",
    "dribbling": "盘带",
    "finishing": "射门",
    "first_touch": "停球",
    "free_kick": "任意球",
    "heading": "头球",
    "long_shots": "远射",
    "long_throws": "界外球",
    "marking": "盯人",
    "passing": "传球",
    "penalty": "点球",
    "tackling": "抢断",
    "technique": "技术",
    "aggression": "侵略性",
    "anticipation": "预判",
    "bravery": "勇敢",
    "composure": "镇定",
    "concentration": "集中",
    "decisions": "决断",
    "determination": "意志力",
    "flair": "想象力",
    "leadership": "领导力",
    "off_the_ball": "无球跑动",
    "positioning": "站位",
    "teamwork": "团队合作",
    "vision": "视野",
    "work_rate": "工作投入",
    "acceleration": "爆发力",
    "agility": "灵活",
    "balance": "平衡",
    "jumping": "弹跳",
    "natural_fitness": "体质",
    "pace": "速度",
    "stamina": "耐力",
    "strength": "强壮",
    "consistency": "稳定性",
    "dirtiness": "肮脏",
    "important_matches": "大赛发挥",
    "injury_proneness": "受伤倾向",
    "versatility": "多样性",
    "adaptability": "适应性",
    "ambition": "野心",
    "controversy": "争议",
    "loyalty": "忠诚",
    "pressure": "抗压",
    "professionalism": "职业素养",
    "sportsmanship": "体育精神",
    "temperament": "情绪控制",
    "aerial_ability": "制空能力",
    "command_of_area": "拦截传中",
    "communication": "指挥防守",
    "eccentricity": "神经指数",
    "handling": "手控球",
    "kicking": "大脚开球",
    "one_on_ones": "一对一",
    "reflexes": "反应",
    "rushing_out": "出击",
    "tendency_to_punch": "击球倾向",
    "throwing": "手抛球",
}


def get_league_info(db: Session):
    return list_league_info(db)


def get_teams(db: Session) -> list[TeamResponse]:
    teams = list_visible_teams(db, VISIBLE_LEVEL)
    sorted_teams = sorted(teams, key=lambda team: (LEVEL_ORDER.get(team.level, 99), team.name))
    overlays = load_team_stat_overlays(db, sorted_teams)
    return [
        build_team_response(
            team,
            overlays.get(team.id, {}),
            build_team_stat_sources(team),
        )
        for team in sorted_teams
    ]


def _build_player_responses(db: Session, players) -> list[PlayerResponse]:
    nationality_map = map_attribute_uid_to_primary_nationality(
        db,
        (player.uid for player in players),
        data_version=get_default_attribute_version(db),
    )
    return [
        build_player_response(player, nationality_map.get(player.uid, player.nationality or ""))
        for player in players
    ]


def get_all_players(db: Session) -> list[PlayerResponse]:
    return _build_player_responses(db, list_players_excluding_team(db, SEA_TEAM_NAME))


def get_players_by_team(db: Session, team_name: str) -> list[PlayerResponse]:
    return _build_player_responses(db, get_players_by_team_name(db, team_name))


def search_player(db: Session, player_name: str) -> list[PlayerResponse]:
    return _build_player_responses(db, search_players_by_name(db, player_name))


def search_player_attributes(
    db: Session,
    player_name: str,
    data_version: str | None = None,
) -> list[AttributeSearchResponse]:
    resolved_version = resolve_attribute_version(db, data_version)
    players = search_player_attributes_by_name(db, player_name, limit=50, data_version=resolved_version)
    heigo_players = map_player_uid_to_team_name(db)
    return [
        build_attribute_search_response(
            player,
            data_version=resolved_version,
            heigo_club=heigo_players.get(player.uid, ATTRIBUTE_FALLBACK_TEAM),
        )
        for player in players
    ]


def _normalize_range_request(field_name: str, value: AdvancedAttributeRangeRequest | None) -> AttributeRangeFilter | None:
    if value is None:
        return None
    minimum = value.min if value.min is not None else None
    maximum = value.max if value.max is not None else None
    if minimum is None and maximum is None:
        return None
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(status_code=400, detail=f"{field_name} 的最小值不能大于最大值")
    return AttributeRangeFilter(field=field_name, minimum=minimum, maximum=maximum)


def _build_range_summary(field_name: str, range_filter: AttributeRangeFilter | None) -> str | None:
    if range_filter is None:
        return None
    label = ADVANCED_SEARCH_FIELD_LABELS.get(field_name, field_name)
    if range_filter.minimum is not None and range_filter.maximum is not None:
        return f"{label} {range_filter.minimum}-{range_filter.maximum}"
    if range_filter.minimum is not None:
        return f"{label} ≥ {range_filter.minimum}"
    return f"{label} ≤ {range_filter.maximum}"


def search_player_attributes_advanced_service(
    db: Session,
    request: AdvancedAttributeSearchRequest,
) -> AdvancedAttributeSearchResponse:
    resolved_version = resolve_attribute_version(db, request.version)
    query_text = str(request.query or "").strip()
    range_filters: list[AttributeRangeFilter] = []
    applied_filters_summary: list[str] = []

    for field_name, range_value in (("age", request.age), ("ca", request.ca), ("pa", request.pa)):
        normalized = _normalize_range_request(field_name, range_value)
        if normalized is not None:
            range_filters.append(normalized)
            applied_filters_summary.append(_build_range_summary(field_name, normalized))

    attribute_field_allowlist = set(ATTRIBUTE_RANGE_FIELD_ALLOWLIST) - {"age", "ca", "pa"}
    invalid_attribute_fields = sorted(set(request.attributes or {}) - attribute_field_allowlist)
    if invalid_attribute_fields:
        raise HTTPException(status_code=400, detail=f"不支持的属性筛选字段: {', '.join(invalid_attribute_fields)}")

    for field_name, range_value in (request.attributes or {}).items():
        normalized = _normalize_range_request(field_name, range_value)
        if normalized is not None:
            range_filters.append(normalized)
            applied_filters_summary.append(_build_range_summary(field_name, normalized))

    position_filters: list[PositionScoreFilter] = []
    invalid_positions = []
    for item in request.positions or []:
        normalized_position = str(item.position or "").strip().upper()
        if normalized_position not in POSITION_SCORE_FIELD_ALLOWLIST:
            invalid_positions.append(normalized_position or "<empty>")
            continue
        if item.min_score < 1 or item.min_score > 20:
            raise HTTPException(status_code=400, detail=f"{normalized_position} 的熟练度下限必须在 1-20 之间")
        position_filters.append(PositionScoreFilter(position=normalized_position, minimum_score=item.min_score))
        applied_filters_summary.append(f"{normalized_position} ≥ {item.min_score}")
    if invalid_positions:
        raise HTTPException(status_code=400, detail=f"不支持的位置筛选字段: {', '.join(sorted(set(invalid_positions)))}")

    if not query_text and not range_filters and not position_filters:
        raise HTTPException(status_code=400, detail="请至少输入关键词或配置一个高级筛选条件")

    result = search_player_attributes_advanced(
        db,
        query_text=query_text,
        range_filters=range_filters,
        position_filters=position_filters,
        limit=request.limit,
        data_version=resolved_version,
    )
    heigo_players = map_player_uid_to_team_name(db)
    return AdvancedAttributeSearchResponse(
        items=[
            build_attribute_search_response(
                player,
                data_version=resolved_version,
                heigo_club=heigo_players.get(player.uid, ATTRIBUTE_FALLBACK_TEAM),
            )
            for player in result.items
        ],
        data_version=resolved_version,
        limit=max(1, min(200, int(request.limit or 200))),
        truncated=result.truncated,
        applied_filters_summary=[item for item in applied_filters_summary if item],
    )


def get_player_attribute_detail(
    db: Session,
    uid: int,
    data_version: str | None = None,
    visitor_token: str | None = None,
) -> PlayerAttributeDetailResponse | None:
    resolved_version = resolve_attribute_version(db, data_version)
    attr = get_player_attribute_by_uid(db, uid, data_version=resolved_version)
    if not attr:
        return None

    heigo_player = get_player_by_uid(db, uid)
    heigo_club = heigo_player.team_name if heigo_player else ATTRIBUTE_FALLBACK_TEAM
    return build_player_attribute_detail_response(
        attr,
        data_version=resolved_version,
        heigo_club=heigo_club,
        reaction_summary=build_player_reaction_summary(db, uid, visitor_token=visitor_token),
    )


def get_attribute_versions(db: Session) -> AttributeVersionsResponse:
    available_versions = list_available_attribute_versions(db)
    return AttributeVersionsResponse(
        available_versions=available_versions,
        default_version=get_default_attribute_version(db),
    )


def get_player_reaction_leaderboard(
    db: Session,
    *,
    metric: str = "flowers",
    limit: int = 20,
    team_name: str | None = None,
    data_version: str | None = None,
) -> PlayerReactionLeaderboardResponse:
    normalized_metric = str(metric or "flowers").strip().lower()
    if normalized_metric not in {"flowers", "eggs", "net"}:
        raise HTTPException(status_code=400, detail="排行榜类型仅支持 flowers、eggs、net。")

    requested_limit = 20 if limit is None else int(limit)
    normalized_limit = max(1, min(100, requested_limit))
    resolved_version = resolve_attribute_version(db, data_version)
    available_versions = list_available_attribute_versions(db)
    attribute_model = get_attribute_model_for_versions(available_versions)
    rows = list_player_reaction_leaderboard_rows(
        db,
        attribute_model=attribute_model,
        data_version=resolved_version,
        metric=normalized_metric,
        team_name=team_name,
        limit=normalized_limit,
    )
    return PlayerReactionLeaderboardResponse(
        metric=normalized_metric,
        limit=normalized_limit,
        team=team_name or None,
        data_version=resolved_version,
        items=[
            build_player_reaction_leaderboard_item_response(
                row,
                data_version=resolved_version,
                fallback_team=ATTRIBUTE_FALLBACK_TEAM,
            )
            for row in rows
        ],
    )


def get_sea_players(db: Session):
    return _build_player_responses(db, get_players_by_team_name(db, SEA_TEAM_NAME))


def get_team_info(db: Session, team_name: str) -> TeamInfoResponse:
    team = get_team_by_name(db, team_name)
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")
    return build_team_info_response(team)


def get_player_wage_detail(db: Session, uid: int) -> WageDetailResponse:
    player = get_player_by_uid(db, uid)
    if not player:
        raise HTTPException(status_code=404, detail="球员不存在")
    return WageDetailResponse.model_validate(
        calculate_player_wage_payload(
            initial_ca=player.initial_ca,
            current_ca=player.ca,
            pa=player.pa,
            age=player.age,
            position=player.position,
            db=db,
        )
    )
