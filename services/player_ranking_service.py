from __future__ import annotations

from sqlalchemy.orm import Session

from models import PlayerCompetitionStat
from schemas_read import PlayerRankingRowResponse, PlayerRankingsResponse

LEAGUE_LEVELS = ["超级", "甲级", "乙级"]


def _rank_rows(rows: list[PlayerCompetitionStat], *, metric: str) -> list[PlayerRankingRowResponse]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -int(getattr(row, metric) or 0),
            -int(row.goals or 0),
            -int(row.assists or 0),
            str(row.player_name or ""),
        ),
    )
    return [
        PlayerRankingRowResponse(
            rank=index,
            level=row.level,
            player_uid=row.player_uid,
            player_name=row.player_name,
            team_id=row.team_id,
            team_name=row.team_name,
            goals=int(row.goals or 0),
            assists=int(row.assists or 0),
            appearances=int(row.appearances or 0),
        )
        for index, row in enumerate(sorted_rows, start=1)
        if int(row.goals or 0) > 0 or int(row.assists or 0) > 0
    ]


def get_player_rankings(db: Session) -> PlayerRankingsResponse:
    stats = db.query(PlayerCompetitionStat).filter(PlayerCompetitionStat.level.in_(LEAGUE_LEVELS)).all()
    rows: list[PlayerRankingRowResponse] = []
    for level in LEAGUE_LEVELS:
        level_rows = [row for row in stats if row.level == level]
        rows.extend(_rank_rows(level_rows, metric="goals"))
    return PlayerRankingsResponse(levels=LEAGUE_LEVELS, rows=rows)
