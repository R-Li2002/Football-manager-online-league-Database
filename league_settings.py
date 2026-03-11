from sqlalchemy.orm import Session

from domain_types import (
    LEAGUE_INFO_DEFINITIONS,
    SUPPORTED_TRANSFER_OPERATIONS,
    coerce_league_info_storage,
    expected_category,
    is_supported_league_info_key,
    serialize_league_info_value,
)
from models import LeagueInfo

LEAGUE_INFO_SCHEMA = {key: definition.category for key, definition in LEAGUE_INFO_DEFINITIONS.items()}


def apply_league_info_value(record: LeagueInfo, raw_value) -> LeagueInfo:
    value_type, int_value, float_value, text_value = coerce_league_info_storage(record.key, raw_value)
    record.category = expected_category(record.key)
    record.value_type = value_type
    record.int_value = int_value
    record.float_value = float_value
    record.text_value = text_value
    return record


def create_league_info_record(key: str, raw_value) -> LeagueInfo:
    record = LeagueInfo(key=key, category=expected_category(key))
    return apply_league_info_value(record, raw_value)


def get_league_info_value(db: Session, key: str, default: str = "") -> str:
    record = db.query(LeagueInfo).filter(LeagueInfo.key == key).first()
    if not record:
        return default
    value = serialize_league_info_value(record.value_type, record.int_value, record.float_value, record.text_value)
    return value if value != "" else default


def get_growth_age_limit(db: Session, default: int = 24) -> int:
    value = get_league_info_value(db, "成长年龄上限", str(default))
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
