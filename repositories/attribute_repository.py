from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from attribute_versions import DEFAULT_ATTRIBUTE_DATA_VERSION, normalize_attribute_data_version, pick_default_attribute_version, sort_attribute_versions
from models import PlayerAttribute, PlayerAttributeVersion
from search_normalization import build_search_normalized_keys

ATTRIBUTE_RANGE_FIELD_ALLOWLIST = {
    "age": "age",
    "ca": "ca",
    "pa": "pa",
    "corner": "corner",
    "crossing": "crossing",
    "dribbling": "dribbling",
    "finishing": "finishing",
    "first_touch": "first_touch",
    "free_kick": "free_kick",
    "heading": "heading",
    "long_shots": "long_shots",
    "long_throws": "long_throws",
    "marking": "marking",
    "passing": "passing",
    "penalty": "penalty",
    "tackling": "tackling",
    "technique": "technique",
    "aggression": "aggression",
    "anticipation": "anticipation",
    "bravery": "bravery",
    "composure": "composure",
    "concentration": "concentration",
    "decisions": "decisions",
    "determination": "determination",
    "flair": "flair",
    "leadership": "leadership",
    "off_the_ball": "off_the_ball",
    "positioning": "positioning",
    "teamwork": "teamwork",
    "vision": "vision",
    "work_rate": "work_rate",
    "acceleration": "acceleration",
    "agility": "agility",
    "balance": "balance",
    "jumping": "jumping",
    "natural_fitness": "natural_fitness",
    "pace": "pace",
    "stamina": "stamina",
    "strength": "strength",
    "consistency": "consistency",
    "dirtiness": "dirtiness",
    "important_matches": "important_matches",
    "injury_proneness": "injury_proneness",
    "versatility": "versatility",
    "adaptability": "adaptability",
    "ambition": "ambition",
    "controversy": "controversy",
    "loyalty": "loyalty",
    "pressure": "pressure",
    "professionalism": "professionalism",
    "sportsmanship": "sportsmanship",
    "temperament": "temperament",
    "aerial_ability": "aerial_ability",
    "command_of_area": "command_of_area",
    "communication": "communication",
    "eccentricity": "eccentricity",
    "handling": "handling",
    "kicking": "kicking",
    "one_on_ones": "one_on_ones",
    "reflexes": "reflexes",
    "rushing_out": "rushing_out",
    "tendency_to_punch": "tendency_to_punch",
    "throwing": "throwing",
}

POSITION_SCORE_FIELD_ALLOWLIST = {
    "GK": "pos_gk",
    "DL": "pos_dl",
    "DC": "pos_dc",
    "DR": "pos_dr",
    "WBL": "pos_wbl",
    "WBR": "pos_wbr",
    "DM": "pos_dm",
    "ML": "pos_ml",
    "MC": "pos_mc",
    "MR": "pos_mr",
    "AML": "pos_aml",
    "AMC": "pos_amc",
    "AMR": "pos_amr",
    "ST": "pos_st",
}


@dataclass(frozen=True)
class AttributeRangeFilter:
    field: str
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class PositionScoreFilter:
    position: str
    minimum_score: int


@dataclass(frozen=True)
class AdvancedAttributeSearchResult:
    items: list[PlayerAttributeVersion | PlayerAttribute]
    truncated: bool


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


def get_attribute_model_for_versions(available_versions: list[str]):
    return PlayerAttributeVersion if available_versions else PlayerAttribute


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
    strict_keys, loose_keys = build_search_normalized_keys(player_name)
    if available_versions:
        query = _query_versioned_attributes(db, resolved_version)
        versioned_filters = []
        for key in strict_keys:
            versioned_filters.append(func.heigo_normalize(PlayerAttributeVersion.name).contains(key))
        for key in loose_keys:
            versioned_filters.append(func.heigo_normalize_loose(PlayerAttributeVersion.name).contains(key))
        if versioned_filters:
            query = query.filter(or_(*versioned_filters))
        else:
            query = query.filter(PlayerAttributeVersion.name.ilike(f"%{player_name}%"))
        return (
            query
            .limit(limit)
            .all()
        )
    legacy_query = _query_legacy_attributes(db)
    legacy_filters = []
    for key in strict_keys:
        legacy_filters.append(func.heigo_normalize(PlayerAttribute.name).contains(key))
    for key in loose_keys:
        legacy_filters.append(func.heigo_normalize_loose(PlayerAttribute.name).contains(key))
    if legacy_filters:
        legacy_query = legacy_query.filter(or_(*legacy_filters))
    else:
        legacy_query = legacy_query.filter(PlayerAttribute.name.ilike(f"%{player_name}%"))
    return legacy_query.limit(limit).all()


def _apply_name_or_uid_filters(query, attribute_model, query_text: str):
    normalized_query = str(query_text or "").strip()
    if not normalized_query:
        return query
    if normalized_query.isdigit():
        return query.filter(attribute_model.uid == int(normalized_query))

    strict_keys, loose_keys = build_search_normalized_keys(normalized_query)
    name_filters = []
    for key in strict_keys:
        name_filters.append(func.heigo_normalize(attribute_model.name).contains(key))
    for key in loose_keys:
        name_filters.append(func.heigo_normalize_loose(attribute_model.name).contains(key))
    if name_filters:
        return query.filter(or_(*name_filters))
    return query.filter(attribute_model.name.ilike(f"%{normalized_query}%"))


def _apply_range_filters(query, attribute_model, filters: Iterable[AttributeRangeFilter]):
    for item in filters:
        column_name = ATTRIBUTE_RANGE_FIELD_ALLOWLIST.get(item.field)
        if not column_name:
            continue
        column = getattr(attribute_model, column_name)
        if item.minimum is not None:
            query = query.filter(column >= item.minimum)
        if item.maximum is not None:
            query = query.filter(column <= item.maximum)
    return query


def _apply_position_filters(query, attribute_model, filters: Iterable[PositionScoreFilter]):
    position_conditions = []
    for item in filters:
        column_name = POSITION_SCORE_FIELD_ALLOWLIST.get(item.position)
        if not column_name:
            continue
        position_conditions.append(getattr(attribute_model, column_name) >= item.minimum_score)
    if position_conditions:
        query = query.filter(or_(*position_conditions))
    return query


def search_player_attributes_advanced(
    db: Session,
    *,
    query_text: str = "",
    range_filters: Iterable[AttributeRangeFilter] = (),
    position_filters: Iterable[PositionScoreFilter] = (),
    limit: int = 200,
    data_version: str | None = None,
) -> AdvancedAttributeSearchResult:
    available_versions = _list_versioned_attribute_versions(db)
    resolved_version = resolve_attribute_version(db, data_version)
    normalized_limit = max(1, min(200, int(limit or 200)))
    attribute_model = PlayerAttributeVersion if available_versions else PlayerAttribute
    query = _query_versioned_attributes(db, resolved_version) if available_versions else _query_legacy_attributes(db)
    query = _apply_name_or_uid_filters(query, attribute_model, query_text)
    query = _apply_range_filters(query, attribute_model, range_filters)
    query = _apply_position_filters(query, attribute_model, position_filters)
    rows = (
        query.order_by(attribute_model.ca.desc(), attribute_model.pa.desc(), attribute_model.uid.asc())
        .limit(normalized_limit + 1)
        .all()
    )
    return AdvancedAttributeSearchResult(
        items=rows[:normalized_limit],
        truncated=len(rows) > normalized_limit,
    )


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
