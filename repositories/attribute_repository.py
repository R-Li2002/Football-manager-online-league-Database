from collections.abc import Iterable

from sqlalchemy.orm import Session

from attribute_versions import DEFAULT_ATTRIBUTE_DATA_VERSION, normalize_attribute_data_version, pick_default_attribute_version, sort_attribute_versions
from models import PlayerAttribute, PlayerAttributeVersion


def _list_versioned_attribute_versions(db: Session) -> list[str]:
    versions = [
        version
        for (version,) in db.query(PlayerAttributeVersion.data_version).distinct().all()
        if normalize_attribute_data_version(version)
    ]
    return sort_attribute_versions(versions)


def list_available_attribute_versions(db: Session) -> list[str]:
    versions = _list_versioned_attribute_versions(db)
    if versions:
        return versions
    has_legacy_rows = db.query(PlayerAttribute.uid).first() is not None
    return [DEFAULT_ATTRIBUTE_DATA_VERSION] if has_legacy_rows else []


def get_default_attribute_version(db: Session) -> str:
    return pick_default_attribute_version(list_available_attribute_versions(db))


def resolve_attribute_version(db: Session, data_version: str | None = None) -> str:
    requested_version = normalize_attribute_data_version(data_version)
    available_versions = list_available_attribute_versions(db)
    if requested_version and requested_version in available_versions:
        return requested_version
    if available_versions:
        return pick_default_attribute_version(available_versions)
    return requested_version or DEFAULT_ATTRIBUTE_DATA_VERSION


def _query_versioned_attributes(db: Session, data_version: str):
    return db.query(PlayerAttributeVersion).filter(PlayerAttributeVersion.data_version == data_version)


def _query_legacy_attributes(db: Session):
    return db.query(PlayerAttribute)


def search_player_attributes_by_name(
    db: Session,
    player_name: str,
    limit: int = 50,
    data_version: str | None = None,
) -> list[PlayerAttributeVersion | PlayerAttribute]:
    available_versions = _list_versioned_attribute_versions(db)
    resolved_version = resolve_attribute_version(db, data_version)
    if available_versions:
        return (
            _query_versioned_attributes(db, resolved_version)
            .filter(PlayerAttributeVersion.name.ilike(f"%{player_name}%"))
            .limit(limit)
            .all()
        )
    return _query_legacy_attributes(db).filter(PlayerAttribute.name.ilike(f"%{player_name}%")).limit(limit).all()


def get_player_attribute_by_uid(
    db: Session,
    uid: int,
    data_version: str | None = None,
) -> PlayerAttributeVersion | PlayerAttribute | None:
    available_versions = _list_versioned_attribute_versions(db)
    resolved_version = resolve_attribute_version(db, data_version)
    if available_versions:
        return (
            _query_versioned_attributes(db, resolved_version)
            .filter(PlayerAttributeVersion.uid == uid)
            .first()
        )
    return _query_legacy_attributes(db).filter(PlayerAttribute.uid == uid).first()


def normalize_attribute_nationality(nationality: str | None) -> str:
    if not nationality:
        return ""
    return next((part.strip() for part in nationality.split(",") if part.strip()), "")


def map_attribute_uid_to_primary_nationality(
    db: Session,
    uids: Iterable[int] | None = None,
    data_version: str | None = None,
) -> dict[int, str]:
    available_versions = _list_versioned_attribute_versions(db)
    resolved_version = resolve_attribute_version(db, data_version)
    if available_versions:
        versioned_query = _query_versioned_attributes(db, resolved_version).with_entities(
            PlayerAttributeVersion.uid,
            PlayerAttributeVersion.nationality,
        )
        if uids:
            versioned_query = versioned_query.filter(PlayerAttributeVersion.uid.in_(list(uids)))
        versioned_rows = versioned_query.all()
        return {
            uid: normalized
            for uid, nationality in versioned_rows
            if (normalized := normalize_attribute_nationality(nationality))
        }

    legacy_query = _query_legacy_attributes(db).with_entities(PlayerAttribute.uid, PlayerAttribute.nationality)
    if uids:
        legacy_query = legacy_query.filter(PlayerAttribute.uid.in_(list(uids)))
    return {
        uid: normalized
        for uid, nationality in legacy_query.all()
        if (normalized := normalize_attribute_nationality(nationality))
    }
