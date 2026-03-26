from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

from imports_runtime.constants import ERROR_DETAIL_SAMPLE_LIMIT, ZERO_WIDTH_RE
from imports_runtime.reporting import DatasetSummary

def normalize_header(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()

def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if hasattr(result, "shape"):
        return False
    try:
        return bool(result)
    except (TypeError, ValueError):
        return False

def clean_string(value: Any, default: str = "") -> str:
    if is_blank(value):
        return default
    return str(value).strip()

def parse_int(value: Any, field_name: str) -> int:
    if is_blank(value):
        raise ValueError(f"{field_name} 不能为空")
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 不是合法整数: {value}") from exc

def parse_optional_int(value: Any, default: int = 0) -> int:
    if is_blank(value):
        return default
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default

def parse_optional_float(value: Any, default: float = 0.0) -> float:
    if is_blank(value):
        return default
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default

def build_column_lookup(df: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for column in df.columns:
        normalized = normalize_header(column)
        if normalized and normalized not in lookup:
            lookup[normalized] = column
    return lookup

def resolve_column(df: pd.DataFrame, aliases: list[str], required: bool = True) -> str | None:
    lookup = build_column_lookup(df)
    for alias in aliases:
        resolved = lookup.get(normalize_header(alias))
        if resolved is not None:
            return resolved
    if required:
        raise KeyError(f"缺少列: {aliases}")
    return None

def apply_model_updates(instance: Any, field_values: dict[str, Any]) -> bool:
    changed = False
    for field_name, new_value in field_values.items():
        if getattr(instance, field_name) != new_value:
            setattr(instance, field_name, new_value)
            changed = True
    return changed

def record_validation_issue(summary: DatasetSummary, issue_type: str, message: str, **issue_data: Any) -> None:
    summary.add_error(message)
    error_counts = summary.details.setdefault("error_counts", {})
    error_counts[issue_type] = error_counts.get(issue_type, 0) + 1
    error_samples = summary.details.setdefault("error_samples", {})
    samples = error_samples.setdefault(issue_type, [])
    if len(samples) < ERROR_DETAIL_SAMPLE_LIMIT:
        samples.append(
            {
                key: value
                for key, value in issue_data.items()
                if value not in (None, "", [], {})
            }
        )

def normalize_team_identifier(value: str) -> str:
    normalized = normalize_header(value).casefold()
    normalized = normalized.replace(".", "").replace("&", "and")
    return normalized
