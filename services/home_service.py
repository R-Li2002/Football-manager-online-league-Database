from datetime import datetime, timezone

from sqlalchemy.orm import Session

from repositories.attribute_repository import count_attribute_players, get_default_attribute_version
from repositories.match_repository import list_matches
from repositories.player_repository import count_league_players
from repositories.team_repository import count_visible_teams, get_team_by_id, list_visible_teams_by_ids
from schemas_read import (
    HomeDashboardLeaderResponse,
    HomeDashboardMatchResponse,
    HomeDashboardResponse,
    HomeDashboardTeamResponse,
)
from services import daily_report_service, data_status_service, match_service

VISIBLE_LEVEL = "隐藏"
LEAGUE_LEVELS = ("超级", "甲级", "乙级")
PLAYED_MATCH_STATUSES = {"played", "home_forfeit", "away_forfeit", "double_forfeit"}


def get_home_summary(db: Session) -> dict[str, int | str]:
    default_attribute_version = get_default_attribute_version(db)
    return {
        "team_count": count_visible_teams(db, VISIBLE_LEVEL),
        "player_count": count_league_players(db),
        "database_player_count": count_attribute_players(db, default_attribute_version),
        "default_attribute_version": default_attribute_version,
    }


def _dashboard_match(match) -> HomeDashboardMatchResponse:
    return HomeDashboardMatchResponse(
        id=match.id,
        level=match.level,
        round_no=match.round_no,
        home_team_id=match.home_team_id,
        home_team_name=match.home_team_name,
        away_team_id=match.away_team_id,
        away_team_name=match.away_team_name,
        home_score=match.home_score,
        away_score=match.away_score,
        status=match.status,
        match_date=match.match_date,
        updated_at=match.updated_at,
    )


def _datetime_sort_value(value: datetime | None, *, fallback: float) -> float:
    if value is None:
        return fallback
    return value.timestamp()


def _played_sort_key(match) -> tuple[float, int, int]:
    return (
        _datetime_sort_value(match.updated_at or match.match_date, fallback=float("-inf")),
        int(match.round_no or 0),
        int(match.id or 0),
    )


def _is_played_match(match) -> bool:
    return bool(
        match.status in PLAYED_MATCH_STATUSES
        and match.home_score is not None
        and match.away_score is not None
    )


def _matches_team(match, team) -> bool:
    if match.home_team_id == team.id or match.away_team_id == team.id:
        return True
    return team.name in {match.home_team_name, match.away_team_name}


def get_home_dashboard(db: Session, *, team_id: int | None = None) -> HomeDashboardResponse:
    data_status = data_status_service.get_data_status(db)
    league_statuses = [
        item
        for item in data_status.items
        if item.key == "schedule" and item.scope in LEAGUE_LEVELS
    ]
    league_statuses.sort(key=lambda item: LEAGUE_LEVELS.index(item.scope))

    matches = [match for match in list_matches(db) if match.level in LEAGUE_LEVELS]
    recent_matches = sorted(
        (match for match in matches if _is_played_match(match)),
        key=_played_sort_key,
        reverse=True,
    )[:4]

    standings = match_service.get_standings(db)
    leader_team_ids = {
        row.team_id
        for row in standings.rows
        if row.level in LEAGUE_LEVELS and row.rank == 1 and row.team_id is not None
    }
    leader_teams = {
        team.id: team
        for team in list_visible_teams_by_ids(db, VISIBLE_LEVEL, leader_team_ids)
    }
    leaders = []
    for level in LEAGUE_LEVELS:
        leader = next((row for row in standings.rows if row.level == level and row.rank == 1), None)
        if not leader:
            continue
        leaders.append(
            HomeDashboardLeaderResponse(
                level=leader.level,
                rank=leader.rank,
                team_id=leader.team_id,
                team_name=leader.team_name,
                manager=leader.manager,
                logo_path=leader_teams.get(leader.team_id).logo_path if leader.team_id in leader_teams else None,
                played=leader.played,
                points=leader.points,
                goal_difference=leader.goal_difference,
            )
        )

    team_summary = None
    team = get_team_by_id(db, team_id)
    if team and team.level in LEAGUE_LEVELS:
        team_matches = [match for match in matches if _matches_team(match, team)]
        upcoming = sorted(
            (
                match
                for match in team_matches
                if match.status in {"scheduled", "postponed"}
                and match.home_score is None
                and match.away_score is None
            ),
            key=lambda match: (
                int(match.round_no or 0),
                _datetime_sort_value(match.match_date, fallback=float("inf")),
                int(match.id or 0),
            ),
        )
        recent_team_results = sorted(
            (match for match in team_matches if _is_played_match(match)),
            key=_played_sort_key,
            reverse=True,
        )
        team_summary = HomeDashboardTeamResponse(
            team_id=team.id,
            team_name=team.name,
            manager=team.manager or "",
            level=team.level,
            logo_path=team.logo_path,
            next_match=_dashboard_match(upcoming[0]) if upcoming else None,
            recent_result=_dashboard_match(recent_team_results[0]) if recent_team_results else None,
        )

    return HomeDashboardResponse(
        generated_at=datetime.now(timezone.utc),
        league_statuses=league_statuses,
        recent_results=[_dashboard_match(match) for match in recent_matches],
        leaders=leaders,
        team=team_summary,
        daily_report=daily_report_service.get_public_report(db),
    )
