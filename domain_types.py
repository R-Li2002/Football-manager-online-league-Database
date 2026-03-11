from dataclasses import dataclass
from enum import Enum


class LeagueInfoValueType(str, Enum):
    INTEGER = "int"
    FLOAT = "float"
    TEXT = "text"


@dataclass(frozen=True)
class LeagueInfoDefinition:
    category: str
    value_type: LeagueInfoValueType


class TransferOperation(str, Enum):
    TRANSFER = "交易"
    FISH = "海捞"
    RELEASE = "解约"
    CONSUME = "消费"
    REJUVENATE = "返老"
    BATCH_TRANSFER = "批量交易"
    BATCH_CONSUME = "批量消费"
    BATCH_RELEASE = "批量解约"


LEAGUE_INFO_DEFINITIONS: dict[str, LeagueInfoDefinition] = {
    "届数": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.INTEGER),
    "本版首届": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.INTEGER),
    "成长年龄上限": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.INTEGER),
    "超级级工资帽": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.FLOAT),
    "甲级级工资帽": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.FLOAT),
    "乙级级工资帽": LeagueInfoDefinition(category="基本信息", value_type=LeagueInfoValueType.FLOAT),
    "总工资": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总平均工资": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总身价": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总平均身价": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "身价极差": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总平均CA": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "CA极差": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总平均PA": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "PA极差": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "总平均成长": LeagueInfoDefinition(category="统计", value_type=LeagueInfoValueType.FLOAT),
    "8M名额系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "7M名额系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "可成长名额系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "非名PA6M系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "非名身价1M系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "非名其他系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
    "GK系数": LeagueInfoDefinition(category="工资系数", value_type=LeagueInfoValueType.FLOAT),
}

SUPPORTED_TRANSFER_OPERATIONS = frozenset(operation.value for operation in TransferOperation)
SLOT_TYPE_8M = "8M"
SLOT_TYPE_7M = "7M"
SLOT_TYPE_FAKE = "伪名"
# Historical mojibake values observed in old SQLite backups before UTF-8 cleanup.
LEGACY_SLOT_TYPE_MOJIBAKE_VALUES = (
    "\u6d7c\ue044\u6095",
    "\u041e\xb1\u0413\u044b",
)
LEGACY_SLOT_TYPE_ALIASES = {value: SLOT_TYPE_FAKE for value in LEGACY_SLOT_TYPE_MOJIBAKE_VALUES}


def is_supported_league_info_key(key: str) -> bool:
    return key in LEAGUE_INFO_DEFINITIONS


def expected_category(key: str) -> str:
    if key not in LEAGUE_INFO_DEFINITIONS:
        raise ValueError(f"Unsupported league info key: {key}")
    return LEAGUE_INFO_DEFINITIONS[key].category


def expected_value_type(key: str) -> str:
    if key not in LEAGUE_INFO_DEFINITIONS:
        raise ValueError(f"Unsupported league info key: {key}")
    return LEAGUE_INFO_DEFINITIONS[key].value_type.value


def normalize_transfer_operation(value: str | TransferOperation) -> str:
    operation = value.value if isinstance(value, TransferOperation) else str(value)
    if operation not in SUPPORTED_TRANSFER_OPERATIONS:
        raise ValueError(f"Unsupported operation: {operation}")
    return operation


def normalize_slot_type(value: str | None) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if not normalized:
        return ""
    return LEGACY_SLOT_TYPE_ALIASES.get(normalized, normalized)


def coerce_league_info_storage(key: str, raw_value) -> tuple[str, int | None, float | None, str | None]:
    value_type = expected_value_type(key)

    if raw_value is None:
        raise ValueError(f"League info value for {key} cannot be null")

    if value_type == LeagueInfoValueType.INTEGER.value:
        parsed = float(raw_value)
        if not parsed.is_integer():
            raise ValueError(f"League info value for {key} must be an integer-compatible number")
        return value_type, int(parsed), None, None

    if value_type == LeagueInfoValueType.FLOAT.value:
        return value_type, None, float(raw_value), None

    return value_type, None, None, str(raw_value)


def parse_league_info_python_value(value_type: str | None, int_value, float_value, text_value):
    if value_type == LeagueInfoValueType.INTEGER.value:
        return int_value
    if value_type == LeagueInfoValueType.FLOAT.value:
        return float_value
    if value_type == LeagueInfoValueType.TEXT.value:
        return text_value
    return None


def serialize_league_info_value(value_type: str | None, int_value, float_value, text_value) -> str:
    python_value = parse_league_info_python_value(value_type, int_value, float_value, text_value)
    if python_value is None:
        return ""
    if value_type == LeagueInfoValueType.FLOAT.value:
        return format(float(python_value), "g")
    return str(python_value)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def transfer_operation_check_sql(column_name: str = "operation") -> str:
    allowed = ", ".join(_sql_literal(value) for value in SUPPORTED_TRANSFER_OPERATIONS)
    return f"{column_name} IN ({allowed})"


def league_info_key_check_sql(column_name: str = "key") -> str:
    allowed = ", ".join(_sql_literal(value) for value in LEAGUE_INFO_DEFINITIONS)
    return f"{column_name} IN ({allowed})"


def league_info_value_type_check_sql(column_name: str = "value_type") -> str:
    allowed = ", ".join(_sql_literal(value.value) for value in LeagueInfoValueType)
    return f"{column_name} IN ({allowed})"


def league_info_payload_check_sql(
    value_type_column: str = "value_type",
    int_column: str = "int_value",
    float_column: str = "float_value",
    text_column: str = "text_value",
) -> str:
    return (
        f"(({value_type_column} = {_sql_literal(LeagueInfoValueType.INTEGER.value)} "
        f"AND {int_column} IS NOT NULL AND {float_column} IS NULL AND {text_column} IS NULL) "
        f"OR ({value_type_column} = {_sql_literal(LeagueInfoValueType.FLOAT.value)} "
        f"AND {float_column} IS NOT NULL AND {int_column} IS NULL AND {text_column} IS NULL) "
        f"OR ({value_type_column} = {_sql_literal(LeagueInfoValueType.TEXT.value)} "
        f"AND {text_column} IS NOT NULL AND {int_column} IS NULL AND {float_column} IS NULL))"
    )


def league_info_key_type_check_sql(key_column: str = "key", value_type_column: str = "value_type") -> str:
    clauses = [
        f"({key_column} = {_sql_literal(key)} AND {value_type_column} = {_sql_literal(definition.value_type.value)})"
        for key, definition in LEAGUE_INFO_DEFINITIONS.items()
    ]
    return "(" + " OR ".join(clauses) + ")"


def league_info_key_category_check_sql(key_column: str = "key", category_column: str = "category") -> str:
    clauses = [
        f"({key_column} = {_sql_literal(key)} AND {category_column} = {_sql_literal(definition.category)})"
        for key, definition in LEAGUE_INFO_DEFINITIONS.items()
    ]
    return "(" + " OR ".join(clauses) + ")"
