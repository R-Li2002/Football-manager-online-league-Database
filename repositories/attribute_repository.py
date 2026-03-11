from sqlalchemy.orm import Session

from models import PlayerAttribute


def search_player_attributes_by_name(db: Session, player_name: str, limit: int = 50) -> list[PlayerAttribute]:
    return db.query(PlayerAttribute).filter(PlayerAttribute.name.ilike(f"%{player_name}%")).limit(limit).all()


def get_player_attribute_by_uid(db: Session, uid: int) -> PlayerAttribute | None:
    return db.query(PlayerAttribute).filter(PlayerAttribute.uid == uid).first()
