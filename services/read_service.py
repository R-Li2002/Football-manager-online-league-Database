from fastapi import HTTPException
from sqlalchemy.orm import Session

from repositories.attribute_repository import (
    get_attribute_model_for_versions,
    get_default_attribute_version,
    get_player_attribute_by_uid,
    list_available_attribute_versions,
    map_attribute_uid_to_primary_nationality,
    resolve_attribute_version,
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
    AttributeSearchResponse,
    AttributeVersionsResponse,
    PlayerAttributeDetailResponse,
    PlayerReactionLeaderboardResponse,
    PlayerResponse,
    TeamInfoResponse,
    TeamResponse,
    WageDetailResponse,
)
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
