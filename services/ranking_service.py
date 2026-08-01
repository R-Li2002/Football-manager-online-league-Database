from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import RankingMatch, RankingSeed, Team
from schemas_read import RankingMatchResponse, RankingsResponse, RankingStandingRowResponse
from schemas_write import RankingMatchCreateRequest
from services.admin_common import LogWriter

LEAGUE_LEVELS = ("超级", "甲级", "乙级")
INITIAL_POINTS = 1000.0
TRANSFER_RATE = 0.1
APPEARANCE_BONUS = 20.0


def _round_points(value: float) -> float:
    return round(float(value), 4)


def _result_label(match: RankingMatch) -> str:
    if int(match.home_score) > int(match.away_score):
        return "home"
    if int(match.home_score) < int(match.away_score):
        return "away"
    return "draw"


def get_rankings(db: Session) -> RankingsResponse:
    teams = db.query(Team).filter(Team.level.in_(LEAGUE_LEVELS)).order_by(Team.name).all()
    seeds = {row.team_id: row for row in db.query(RankingSeed).all()}
    states = {}
    for team in teams:
        seed = seeds.get(team.id)
        states[team.id] = {
            "team": team,
            "base_points": float(seed.base_points) if seed else INITIAL_POINTS,
            "matches": int(seed.matches or 0) if seed else 0,
            "wins": int(seed.wins or 0) if seed else 0,
            "draws": int(seed.draws or 0) if seed else 0,
            "losses": int(seed.losses or 0) if seed else 0,
        }

    matches = db.query(RankingMatch).order_by(RankingMatch.played_at, RankingMatch.id).all()
    valid_matches = []
    for match in matches:
        home = states.get(match.home_team_id)
        away = states.get(match.away_team_id)
        if not home or not away:
            continue
        valid_matches.append(match)
        home["matches"] += 1
        away["matches"] += 1
        if match.home_score == match.away_score:
            home["draws"] += 1
            away["draws"] += 1
            continue
        winner, loser = (home, away) if match.home_score > match.away_score else (away, home)
        transferred = float(loser["base_points"]) * TRANSFER_RATE
        winner["base_points"] = float(winner["base_points"]) + transferred
        loser["base_points"] = float(loser["base_points"]) - transferred
        winner["wins"] += 1
        loser["losses"] += 1

    ordered = sorted(
        states.values(),
        key=lambda row: (
            -(float(row["base_points"]) + int(row["matches"]) * APPEARANCE_BONUS),
            -float(row["base_points"]),
            -int(row["wins"]),
            str(row["team"].name or ""),
        ),
    )
    rows = [
        RankingStandingRowResponse(
            rank=index,
            team_id=int(row["team"].id),
            team_name=str(row["team"].name),
            level=str(row["team"].level),
            logo_path=row["team"].logo_path,
            base_points=_round_points(row["base_points"]),
            total_points=_round_points(float(row["base_points"]) + int(row["matches"]) * APPEARANCE_BONUS),
            matches=int(row["matches"]),
            wins=int(row["wins"]),
            draws=int(row["draws"]),
            losses=int(row["losses"]),
        )
        for index, row in enumerate(ordered, start=1)
    ]
    match_rows = [
        RankingMatchResponse(
            id=int(match.id),
            home_team_id=int(match.home_team_id),
            home_team_name=str(match.home_team_name),
            away_team_id=int(match.away_team_id),
            away_team_name=str(match.away_team_name),
            home_score=int(match.home_score),
            away_score=int(match.away_score),
            result=_result_label(match),
            played_at=match.played_at,
        )
        for match in reversed(valid_matches)
    ]
    return RankingsResponse(
        initial_points=INITIAL_POINTS,
        appearance_bonus=APPEARANCE_BONUS,
        transfer_rate=TRANSFER_RATE,
        total_matches=len(valid_matches),
        rows=rows,
        matches=match_rows,
    )


def create_ranking_match(
    db: Session,
    operator: str,
    request: RankingMatchCreateRequest,
    write_to_log: LogWriter,
) -> RankingsResponse:
    if int(request.home_team_id) == int(request.away_team_id):
        raise HTTPException(status_code=400, detail="排位比赛双方不能是同一支球队")
    teams = {
        team.id: team
        for team in db.query(Team)
        .filter(Team.id.in_([request.home_team_id, request.away_team_id]), Team.level.in_(LEAGUE_LEVELS))
        .all()
    }
    home = teams.get(request.home_team_id)
    away = teams.get(request.away_team_id)
    if not home or not away:
        raise HTTPException(status_code=400, detail="排位比赛只能选择当前三级联赛球队")
    match = RankingMatch(
        home_team_id=home.id,
        home_team_name=home.name,
        away_team_id=away.id,
        away_team_name=away.name,
        home_score=int(request.home_score),
        away_score=int(request.away_score),
        created_by=operator,
        played_at=datetime.now(),
        created_at=datetime.now(),
    )
    db.add(match)
    db.commit()
    write_to_log("排位比赛录入", f"{home.name} {match.home_score}:{match.away_score} {away.name}", operator)
    return get_rankings(db)


def delete_ranking_match(
    db: Session,
    operator: str,
    match_id: int,
    write_to_log: LogWriter,
) -> RankingsResponse:
    match = db.query(RankingMatch).filter(RankingMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="排位比赛不存在")
    detail = f"{match.home_team_name} {match.home_score}:{match.away_score} {match.away_team_name}"
    db.delete(match)
    db.commit()
    write_to_log("排位比赛撤销", detail, operator)
    return get_rankings(db)
