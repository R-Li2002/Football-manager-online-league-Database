from __future__ import annotations

from decimal import Decimal, InvalidOperation
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pandas as pd

from imports_runtime.constants import (
    ATTRIBUTE_HEADER_CANONICAL_RENAMES,
    ATTRIBUTE_XLSX_HEADER_SCAN_ROWS,
    ATTRIBUTE_XLSX_SHEET_INDEX,
    DERIVED_RADAR_AVERAGE_RECIPES,
    DERIVED_RADAR_COPY_RECIPES,
    IEEE754_SAFE_INTEGER_MAX,
    MAX_SAFE_PLAYER_HABIT_COUNT,
    NUMERIC_HABIT_CODE_RE,
    PLAYER_HABIT_BIT_LABELS,
    PLAYER_HABIT_HIGH_BITS_COLUMN,
    PLAYER_HABIT_KNOWN_MASK,
    PLAYER_HABIT_RAW_CODE_COLUMN,
    PLAYER_HABIT_TEXT_COLUMN,
)
from imports_runtime.validators import clean_string, is_blank, normalize_header

def parse_player_habit_code(value: Any) -> tuple[int, str, bool] | None:
    if is_blank(value) or isinstance(value, bool):
        return None

    if isinstance(value, Integral):
        number = int(value)
        return (number, str(number), True) if number >= 0 else None

    if isinstance(value, Real):
        number = float(value)
        if pd.isna(number) or not number.is_integer():
            return None
        normalized = int(number)
        if normalized < 0:
            return None
        return normalized, str(normalized), normalized <= IEEE754_SAFE_INTEGER_MAX

    text = clean_string(value)
    if not text or not NUMERIC_HABIT_CODE_RE.fullmatch(text):
        return None

    try:
        decimal_value = Decimal(text)
    except InvalidOperation:
        return None

    if decimal_value != decimal_value.to_integral_value():
        return None

    normalized = int(decimal_value)
    if normalized < 0:
        return None

    is_exact_integer = "e" not in text.casefold() and "." not in text
    return normalized, str(normalized), is_exact_integer

def decode_player_habit_value(value: Any) -> dict[str, Any] | None:
    parsed = parse_player_habit_code(value)
    if parsed is None:
        return None

    numeric_code, raw_code, is_exact = parsed
    low_bits = numeric_code & PLAYER_HABIT_KNOWN_MASK
    high_bits = numeric_code & ~PLAYER_HABIT_KNOWN_MASK
    bit_count = numeric_code.bit_count()
    is_reliable = is_exact and bit_count <= MAX_SAFE_PLAYER_HABIT_COUNT
    decoded_text = ""
    if is_reliable and low_bits:
        decoded_text = "\n".join(label for bit, label in PLAYER_HABIT_BIT_LABELS if low_bits & bit)

    return {
        "decoded_text": decoded_text,
        "raw_code": raw_code if numeric_code != 0 else "",
        "high_bits": str(high_bits) if high_bits else "",
        "is_reliable": is_reliable,
        "bit_count": bit_count,
    }

def decode_player_habits(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    if PLAYER_HABIT_TEXT_COLUMN not in df.columns:
        return df, {
            "player_habit_numeric_rows": 0,
            "player_habit_decoded_rows": 0,
            "player_habit_high_bits_rows": 0,
            "player_habit_unresolved_rows": 0,
        }

    habit_texts: list[str] = []
    raw_codes: list[str] = []
    high_bits_codes: list[str] = []
    numeric_rows = 0
    decoded_rows = 0
    high_bits_rows = 0
    unresolved_rows = 0

    for raw_value in df[PLAYER_HABIT_TEXT_COLUMN].tolist():
        decoded = decode_player_habit_value(raw_value)
        if decoded is None:
            habit_texts.append(clean_string(raw_value))
            raw_codes.append("")
            high_bits_codes.append("")
            continue

        numeric_rows += 1
        raw_codes.append(decoded["raw_code"])
        high_bits_codes.append(decoded["high_bits"])
        if decoded["high_bits"]:
            high_bits_rows += 1
        if decoded["is_reliable"] and decoded["decoded_text"]:
            habit_texts.append(decoded["decoded_text"])
            decoded_rows += 1
        else:
            habit_texts.append("")
            unresolved_rows += 1

    additions = {
        PLAYER_HABIT_TEXT_COLUMN: pd.Series(habit_texts, index=df.index, dtype=object),
        PLAYER_HABIT_RAW_CODE_COLUMN: pd.Series(raw_codes, index=df.index, dtype=object),
        PLAYER_HABIT_HIGH_BITS_COLUMN: pd.Series(high_bits_codes, index=df.index, dtype=object),
    }
    df = pd.concat([df.drop(columns=[PLAYER_HABIT_TEXT_COLUMN], errors="ignore"), pd.DataFrame(additions)], axis=1)
    return df, {
        "player_habit_numeric_rows": numeric_rows,
        "player_habit_decoded_rows": decoded_rows,
        "player_habit_high_bits_rows": high_bits_rows,
        "player_habit_unresolved_rows": unresolved_rows,
    }

def read_csv_with_fallback_encodings(path: Path) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, dtype=object, low_memory=False, encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc
            break
    if last_error is None:
        raise ValueError(f"无法读取属性文件: {path}")
    raise last_error

def dedupe_headers(headers: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    deduped: list[str] = []
    for index, value in enumerate(headers):
        base = clean_string(value, default=f"Unnamed: {index}")
        counter = seen.get(base, 0)
        deduped.append(base if counter == 0 else f"{base}.{counter}")
        seen[base] = counter + 1
    return deduped

def detect_attribute_workbook_header_row(preview: pd.DataFrame) -> int:
    best_row = 0
    best_score = -1
    for row_index in preview.index:
        cells = [normalize_header(value) for value in preview.loc[row_index].tolist() if not is_blank(value)]
        if not cells:
            continue
        text_like = sum(not cell.isdigit() for cell in cells)
        score = text_like * 100 + len(cells)
        if text_like >= max(8, len(cells) // 2) and score > best_score:
            best_row = int(row_index)
            best_score = score
    return best_row

def read_attribute_workbook(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    with pd.ExcelFile(path) as workbook:
        sheet_name = workbook.sheet_names[ATTRIBUTE_XLSX_SHEET_INDEX]
        preview = workbook.parse(
            sheet_name=sheet_name,
            header=None,
            nrows=ATTRIBUTE_XLSX_HEADER_SCAN_ROWS,
            dtype=object,
        )
        header_row = detect_attribute_workbook_header_row(preview)
        raw_df = workbook.parse(sheet_name=sheet_name, header=None, dtype=object)

    headers = dedupe_headers(raw_df.iloc[header_row].tolist())
    df = raw_df.iloc[header_row + 1 :].reset_index(drop=True)
    df.columns = headers
    metadata = {
        "source_format": "xlsx",
        "sheet_name": sheet_name,
        "header_row": header_row + 1,
    }
    return df, metadata

def canonicalize_attribute_headers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    rename_lookup = {
        normalize_header(source): target
        for source, target in ATTRIBUTE_HEADER_CANONICAL_RENAMES.items()
    }
    renamed_headers: dict[str, str] = {}
    rename_map: dict[str, str] = {}
    existing_headers = set(df.columns)

    for column in df.columns:
        canonical = rename_lookup.get(normalize_header(column))
        if canonical is None or canonical == column:
            continue
        if canonical in existing_headers and canonical != column:
            continue
        rename_map[column] = canonical
        renamed_headers[column] = canonical
        existing_headers.add(canonical)

    if rename_map:
        df = df.rename(columns=rename_map)
    return df, renamed_headers

def apply_negative_pa_override(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if "负潜" not in df.columns:
        return df, 0

    negative_pa = pd.to_numeric(df["负潜"], errors="coerce")
    override_mask = negative_pa.notna() & (negative_pa != 0)
    if not override_mask.any():
        return df, 0

    if "pa" in df.columns:
        pa_series = pd.to_numeric(df["pa"], errors="coerce")
        df = df.copy()
        df["pa"] = pa_series.where(~override_mask, negative_pa)
    else:
        df = df.copy()
        df["pa"] = negative_pa.where(override_mask)

    return df, int(override_mask.sum())

def add_derived_radar_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    derived_columns: list[str] = []
    additions: dict[str, pd.Series] = {}

    def get_numeric_series(column_name: str) -> pd.Series:
        if column_name in additions:
            return additions[column_name]
        return pd.to_numeric(df[column_name], errors="coerce")

    for target, source_columns in DERIVED_RADAR_AVERAGE_RECIPES.items():
        if target in df.columns or any(source not in df.columns and source not in additions for source in source_columns):
            continue
        numeric_source = [get_numeric_series(source) for source in source_columns]
        additions[target] = pd.concat(numeric_source, axis=1).mean(axis=1)
        derived_columns.append(target)

    for target, source in DERIVED_RADAR_COPY_RECIPES.items():
        if target in df.columns or (source not in df.columns and source not in additions):
            continue
        additions[target] = get_numeric_series(source)
        derived_columns.append(target)

    if additions:
        df = pd.concat([df, pd.DataFrame(additions, index=df.index)], axis=1)

    return df, derived_columns

def load_player_attributes_source(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    suffix = path.suffix.lower()
    metadata: dict[str, Any]
    if suffix == ".csv":
        df, encoding = read_csv_with_fallback_encodings(path)
        metadata = {"source_format": "csv", "encoding": encoding}
    elif suffix in {".xlsx", ".xls"}:
        df, metadata = read_attribute_workbook(path)
    else:
        raise ValueError(f"不支持的属性文件格式: {path.suffix}")

    df, renamed_headers = canonicalize_attribute_headers(df)
    df, negative_pa_override_count = apply_negative_pa_override(df)
    df, player_habit_decode_stats = decode_player_habits(df)
    df, derived_columns = add_derived_radar_columns(df)
    metadata["renamed_headers"] = renamed_headers
    metadata["derived_columns"] = derived_columns
    metadata["negative_pa_override_count"] = negative_pa_override_count
    metadata.update(player_habit_decode_stats)
    return df, metadata
