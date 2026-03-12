from collections.abc import Iterable

from sqlalchemy.orm import Session

from models import PlayerAttribute


def search_player_attributes_by_name(db: Session, player_name: str, limit: int = 50) -> list[PlayerAttribute]:
    return db.query(PlayerAttribute).filter(PlayerAttribute.name.ilike(f"%{player_name}%")).limit(limit).all()


def get_player_attribute_by_uid(db: Session, uid: int) -> PlayerAttribute | None:
    return db.query(PlayerAttribute).filter(PlayerAttribute.uid == uid).first()


def normalize_attribute_nationality(nationality: str | None) -> str:
    if not nationality:
        return ""
    return next((part.strip() for part in nationality.split(",") if part.strip()), "")


def map_attribute_uid_to_primary_nationality(
    db: Session, uids: Iterable[int] | None = None
) -> dict[int, str]:
    query = db.query(PlayerAttribute.uid, PlayerAttribute.nationality)
    if uids:
        query = query.filter(PlayerAttribute.uid.in_(list(uids)))
    return {
        uid: normalized
        for uid, nationality in query.all()
        if (normalized := normalize_attribute_nationality(nationality))
    }
