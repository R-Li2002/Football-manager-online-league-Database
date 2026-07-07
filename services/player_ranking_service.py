from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import Match, MatchPlayerEvent, PlayerCompetitionStat
from schemas_read import PlayerRankingRowResponse, PlayerRankingsResponse

LEAGUE_LEVELS = ["超级", "甲级", "乙级"]


def _rank_rows(rows: list[dict], *, metric: str) -> list[PlayerRankingRowResponse]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -int(row.get(metric) or 0),
            -int(row.get("goals") or 0),
            -int(row.get("assists") or 0),
            -int(row.get("mvps") or 0),
            str(row.get("player_name") or ""),
        ),
    )
    return [
        PlayerRankingRowResponse(
            rank=index,
            level=row["level"],
            player_uid=row["player_uid"],
            player_name=row["player_name"],
            team_id=row["team_id"],
            team_name=row["team_name"],
            goals=int(row.get("goals") or 0),
            assists=int(row.get("assists") or 0),
            mvps=int(row.get("mvps") or 0),
            appearances=int(row.get("appearances") or 0),
        )
        for index, row in enumerate(sorted_rows, start=1)
        if int(row.get("goals") or 0) > 0 or int(row.get("assists") or 0) > 0 or int(row.get("mvps") or 0) > 0
    ]


def get_player_rankings(db: Session) -> PlayerRankingsResponse:
    stats_by_key: dict[tuple[str, int | None, str, str], dict] = {}
    event_rows = (
        db.query(
            Match.level.label("level"),
            MatchPlayerEvent.player_uid.label("player_uid"),
            MatchPlayerEvent.player_name.label("player_name"),
            MatchPlayerEvent.team_id.label("team_id"),
            MatchPlayerEvent.team_name.label("team_name"),
            func.sum(case((MatchPlayerEvent.event_type == "goal", MatchPlayerEvent.quantity), else_=0)).label("goals"),
            func.sum(case((MatchPlayerEvent.event_type == "assist", MatchPlayerEvent.quantity), else_=0)).label("assists"),
            func.sum(case((MatchPlayerEvent.event_type == "mvp", MatchPlayerEvent.quantity), else_=0)).label("mvps"),
            func.count(func.distinct(MatchPlayerEvent.match_id)).label("appearances"),
        )
        .join(Match, Match.id == MatchPlayerEvent.match_id)
        .filter(Match.level.in_(LEAGUE_LEVELS), Match.status == "played")
        .group_by(
            Match.level,
            MatchPlayerEvent.player_uid,
            MatchPlayerEvent.player_name,
            MatchPlayerEvent.team_id,
            MatchPlayerEvent.team_name,
        )
        .all()
    )
    for row in event_rows:
        key = (row.level, row.player_uid, row.player_name, row.team_name)
        stats_by_key[key] = {
            "level": row.level,
            "player_uid": row.player_uid,
            "player_name": row.player_name,
            "team_id": row.team_id,
            "team_name": row.team_name,
            "goals": int(row.goals or 0),
            "assists": int(row.assists or 0),
            "mvps": int(row.mvps or 0),
            "appearances": int(row.appearances or 0),
        }

    legacy_stats = db.query(PlayerCompetitionStat).filter(PlayerCompetitionStat.level.in_(LEAGUE_LEVELS)).all()
    for row in legacy_stats:
        key = (row.level, row.player_uid, row.player_name, row.team_name)
        if key in stats_by_key:
            stats_by_key[key]["appearances"] = max(stats_by_key[key]["appearances"], int(row.appearances or 0))
            continue
        stats_by_key[key] = {
            "level": row.level,
            "player_uid": row.player_uid,
            "player_name": row.player_name,
            "team_id": row.team_id,
            "team_name": row.team_name,
            "goals": int(row.goals or 0),
            "assists": int(row.assists or 0),
            "mvps": 0,
            "appearances": int(row.appearances or 0),
        }

    stats = list(stats_by_key.values())
    rows: list[PlayerRankingRowResponse] = []
    for level in LEAGUE_LEVELS:
        level_rows = [row for row in stats if row["level"] == level]
        rows.extend(_rank_rows(level_rows, metric="goals"))
    return PlayerRankingsResponse(levels=LEAGUE_LEVELS, rows=rows)
