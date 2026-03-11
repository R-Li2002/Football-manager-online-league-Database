from sqlalchemy.orm import Session

from models import Team


def get_team_by_name(db: Session, team_name: str) -> Team | None:
    return db.query(Team).filter(Team.name == team_name).first()


def get_team_by_id(db: Session, team_id: int | None) -> Team | None:
    if not team_id:
        return None
    return db.query(Team).filter(Team.id == team_id).first()


def get_other_team_by_name(db: Session, team_name: str, excluded_team_id: int) -> Team | None:
    return db.query(Team).filter(Team.name == team_name, Team.id != excluded_team_id).first()


def list_visible_teams(db: Session, hidden_level: str) -> list[Team]:
    return db.query(Team).filter(Team.level != hidden_level).all()


def list_visible_teams_by_ids(db: Session, hidden_level: str, team_ids: set[int]) -> list[Team]:
    if not team_ids:
        return []
    return db.query(Team).filter(Team.level != hidden_level, Team.id.in_(team_ids)).all()


def count_visible_teams(db: Session, hidden_level: str) -> int:
    return db.query(Team).filter(Team.level != hidden_level).count()


def count_visible_teams_with_unknown_cache_refresh(db: Session, hidden_level: str, unknown_mode: str) -> int:
    return (
        db.query(Team)
        .filter(Team.level != hidden_level)
        .filter((Team.stats_cache_refresh_mode.is_(None)) | (Team.stats_cache_refresh_mode == unknown_mode))
        .count()
    )
