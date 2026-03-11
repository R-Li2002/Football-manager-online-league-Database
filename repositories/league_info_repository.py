from sqlalchemy.orm import Session

from models import LeagueInfo


def list_league_info(db: Session) -> list[LeagueInfo]:
    return db.query(LeagueInfo).order_by(LeagueInfo.category, LeagueInfo.id).all()
