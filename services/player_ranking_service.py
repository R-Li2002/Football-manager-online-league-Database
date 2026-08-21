from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models import Match, MatchPlayerEvent, PlayerCompetitionStat
from schemas_read import PlayerRankingCoverageResponse, PlayerRankingRowResponse, PlayerRankingsResponse

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


def _build_coverage(db: Session, *, levels: list[str] | None = None) -> list[PlayerRankingCoverageResponse]:
    active_levels = levels or LEAGUE_LEVELS
    coverage_by_level: dict[str, dict[str, int | str]] = {
        level: {
            "level": level,
            "played_matches": 0,
            "matches_with_events": 0,
            "matches_missing_events": 0,
            "event_rows": 0,
            "goal_quantity": 0,
            "assist_quantity": 0,
            "mvp_quantity": 0,
        }
        for level in active_levels
    }

    played_rows = (
        db.query(Match.level.label("level"), func.count(Match.id).label("played_matches"))
        .filter(Match.level.in_(active_levels), Match.status == "played")
        .group_by(Match.level)
        .all()
    )
    for row in played_rows:
        if row.level in coverage_by_level:
            coverage_by_level[row.level]["played_matches"] = int(row.played_matches or 0)

    event_match_rows = (
        db.query(
            Match.level.label("level"),
            func.count(func.distinct(MatchPlayerEvent.match_id)).label("matches_with_events"),
            func.count(MatchPlayerEvent.id).label("event_rows"),
            func.sum(case((MatchPlayerEvent.event_type == "goal", MatchPlayerEvent.quantity), else_=0)).label("goal_quantity"),
            func.sum(case((MatchPlayerEvent.event_type == "assist", MatchPlayerEvent.quantity), else_=0)).label("assist_quantity"),
            func.sum(case((MatchPlayerEvent.event_type == "mvp", MatchPlayerEvent.quantity), else_=0)).label("mvp_quantity"),
        )
        .join(Match, Match.id == MatchPlayerEvent.match_id)
        .filter(Match.level.in_(active_levels), Match.status == "played")
        .group_by(Match.level)
        .all()
    )
    for row in event_match_rows:
        if row.level not in coverage_by_level:
            continue
        coverage_by_level[row.level]["matches_with_events"] = int(row.matches_with_events or 0)
        coverage_by_level[row.level]["event_rows"] = int(row.event_rows or 0)
        coverage_by_level[row.level]["goal_quantity"] = int(row.goal_quantity or 0)
        coverage_by_level[row.level]["assist_quantity"] = int(row.assist_quantity or 0)
        coverage_by_level[row.level]["mvp_quantity"] = int(row.mvp_quantity or 0)

    for row in coverage_by_level.values():
        row["matches_missing_events"] = max(0, int(row["played_matches"] or 0) - int(row["matches_with_events"] or 0))

    return [PlayerRankingCoverageResponse(**coverage_by_level[level]) for level in active_levels]


def get_player_rankings(db: Session, *, level: str | None = None) -> PlayerRankingsResponse:
    active_levels = [level] if level else LEAGUE_LEVELS
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
        .filter(Match.level.in_(active_levels), Match.status == "played")
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

    legacy_stats = db.query(PlayerCompetitionStat).filter(PlayerCompetitionStat.level.in_(active_levels)).all()
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
    for active_level in active_levels:
        level_rows = [row for row in stats if row["level"] == active_level]
        rows.extend(_rank_rows(level_rows, metric="goals"))
    return PlayerRankingsResponse(levels=active_levels, rows=rows, coverage=_build_coverage(db, levels=active_levels))


def get_team_player_rankings(
    db: Session,
    *,
    level: str,
    team_id: int | None = None,
    team_name: str | None = None,
) -> PlayerRankingsResponse:
    """Return one team's rows from the canonical player-ranking calculation."""
    rankings = get_player_rankings(db, level=level)
    normalized_team_id = int(team_id or 0)
    normalized_team_name = str(team_name or "").strip()
    rows = [
        row
        for row in rankings.rows
        if (
            (normalized_team_id > 0 and int(row.team_id or 0) == normalized_team_id)
            or (normalized_team_name and row.team_name == normalized_team_name)
        )
    ]
    return PlayerRankingsResponse(levels=[level], rows=rows, coverage=rankings.coverage)
