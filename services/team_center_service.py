from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Team
from schemas_read import ScheduleResponse, StandingsResponse, SuspensionsResponse, TeamCenterResponse, TeamPowerSummariesResponse
from services import cup_service, player_power_ranking_service, read_service, suspension_service, team_lineup_service


def _belongs_to_team(match, team: Team) -> bool:
    return bool(
        int(match.home_team_id or 0) == int(team.id)
        or int(match.away_team_id or 0) == int(team.id)
        or match.home_team_name == team.name
        or match.away_team_name == team.name
    )


def get_team_center(
    db: Session,
    team_id: int,
    *,
    admin_session_token: str | None = None,
    coach_session_token: str | None = None,
) -> TeamCenterResponse:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")

    team_response = next((item for item in read_service.get_teams(db) if int(item.id) == int(team.id)), None)
    if not team_response:
        raise HTTPException(status_code=404, detail="球队不在当前联赛范围内")

    standings = read_service.get_standings(db)
    team_standings = StandingsResponse(
        levels=[team.level],
        rows=[row for row in standings.rows if int(row.team_id or 0) == int(team.id) or row.team_name == team.name],
    )

    level_schedule = read_service.get_schedule(db, level=team.level)
    team_matches = [match for match in level_schedule.matches if _belongs_to_team(match, team)]
    team_schedule = ScheduleResponse(
        levels=[team.level],
        rounds=sorted({int(match.round_no) for match in team_matches}),
        matches=team_matches,
    )

    suspensions = suspension_service.get_suspensions(db, team_id=team.id)
    team_suspensions = SuspensionsResponse(
        levels=[team.level],
        teams=[
            item
            for item in suspensions.teams
            if int(item.team_id or 0) == int(team.id) or item.team_name == team.name
        ],
    )

    power_summaries = player_power_ranking_service.get_team_power_summaries(db)
    level_power_summaries = TeamPowerSummariesResponse(
        data_version=power_summaries.data_version,
        items=[item for item in power_summaries.items if item.level == team.level],
    )

    return TeamCenterResponse(
        team=team_response,
        players=read_service.get_players_by_team(db, team.name),
        standings=team_standings,
        matches=team_schedule,
        suspensions=team_suspensions,
        power=player_power_ranking_service.get_player_power_ranking(
            db,
            shape="all",
            limit="all",
            team_name=team.name,
            data_version=power_summaries.data_version,
        ),
        lineup=team_lineup_service.get_team_lineup(
            db,
            team.id,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
        ),
        team_power_summaries=level_power_summaries,
        cup_outlook=cup_service.get_team_cup_outlook(db, team.id),
    )
