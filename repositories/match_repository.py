from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models import Match, MatchPlayerEvent


def list_matches(db: Session, *, level: str | None = None, round_no: int | None = None) -> list[Match]:
    query = db.query(Match)
    if level:
        query = query.filter(Match.level == level)
    if round_no is not None:
        query = query.filter(Match.round_no == round_no)
    return query.order_by(Match.level, Match.round_no, Match.id).all()


def list_match_events(db: Session, match_ids: set[int] | None = None) -> list[MatchPlayerEvent]:
    query = db.query(MatchPlayerEvent)
    if match_ids is not None:
        if not match_ids:
            return []
        query = query.filter(MatchPlayerEvent.match_id.in_(match_ids))
    return query.order_by(MatchPlayerEvent.match_id, MatchPlayerEvent.id).all()


def delete_match_events(db: Session, match_id: int) -> None:
    db.query(MatchPlayerEvent).filter(MatchPlayerEvent.match_id == match_id).delete(synchronize_session=False)


def list_played_matches(db: Session) -> list[Match]:
    return (
        db.query(Match)
        .filter(
            Match.status.in_(("played", "home_forfeit", "away_forfeit", "double_forfeit")),
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        )
        .order_by(Match.level, Match.round_no, Match.id)
        .all()
    )


def get_match_by_id(db: Session, match_id: int) -> Match | None:
    return db.query(Match).filter(Match.id == match_id).first()


def find_match_by_fixture(
    db: Session,
    *,
    level: str,
    round_no: int,
    home_team_name: str,
    away_team_name: str,
) -> Match | None:
    return (
        db.query(Match)
        .filter(
            Match.level == level,
            Match.round_no == round_no,
            Match.home_team_name == home_team_name,
            Match.away_team_name == away_team_name,
        )
        .first()
    )


def delete_matches_not_in_keys(db: Session, fixture_keys: set[tuple[str, int, str, str]]) -> int:
    existing = db.query(Match).all()
    removed = 0
    for match in existing:
        key = (match.level, match.round_no, match.home_team_name, match.away_team_name)
        if key not in fixture_keys:
            db.delete(match)
            removed += 1
    return removed


def list_matches_for_team_names(db: Session, team_names: set[str]) -> list[Match]:
    if not team_names:
        return []
    return (
        db.query(Match)
        .filter(or_(Match.home_team_name.in_(team_names), Match.away_team_name.in_(team_names)))
        .order_by(Match.level, Match.round_no, Match.id)
        .all()
    )
