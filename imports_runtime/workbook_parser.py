from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from imports_runtime.constants import (
    PLAYER_TEAM_MAP_COLUMN_ALIASES,
    TEAM_NAME_ALIASES,
    WORKBOOK_SHEET_PLAYER_TEAM_MAP,
)
from imports_runtime.reporting import DatasetSummary
from imports_runtime.validators import clean_string, is_blank, normalize_header, normalize_team_identifier, parse_int, resolve_column
from models import Team

def get_workbook_sheet_names(workbook_path: str) -> tuple[str, ...]:
    with pd.ExcelFile(workbook_path) as workbook:
        return tuple(workbook.sheet_names)

def resolve_sheet_name(workbook_path: Path, requested_sheet_name: str) -> str:
    normalized_requested = normalize_header(requested_sheet_name)
    sheet_names = get_workbook_sheet_names(str(workbook_path))
    for sheet_name in sheet_names:
        if normalize_header(sheet_name) == normalized_requested:
            return sheet_name
    raise KeyError(f"工作簿缺少工作表: {requested_sheet_name}；可用工作表: {list(sheet_names)}")

def load_excel(workbook_path: Path, sheet_name: str, header: int | None) -> pd.DataFrame:
    resolved_sheet_name = resolve_sheet_name(workbook_path, sheet_name)
    return pd.read_excel(workbook_path, sheet_name=resolved_sheet_name, header=header, dtype=object)

def resolve_team_name(team_name: str, teams_by_name: dict[str, Team], normalized_team_names: dict[str, str]) -> str:
    raw_team_name = clean_string(team_name)
    if not raw_team_name:
        return ""
    if raw_team_name in teams_by_name:
        return raw_team_name

    normalized = normalize_team_identifier(raw_team_name)
    direct_match = normalized_team_names.get(normalized)
    if direct_match:
        return direct_match

    aliased = TEAM_NAME_ALIASES.get(raw_team_name)
    if aliased:
        return aliased

    alias_match = normalized_team_names.get(normalize_team_identifier(raw_team_name))
    if alias_match:
        return alias_match

    return raw_team_name

def load_player_team_overrides(workbook_path: Path, summary: DatasetSummary) -> dict[int, dict[str, str]]:
    try:
        df = load_excel(workbook_path, WORKBOOK_SHEET_PLAYER_TEAM_MAP, header=0)
    except Exception as exc:
        summary.add_warning(f"未加载 {WORKBOOK_SHEET_PLAYER_TEAM_MAP}，将仅使用联赛名单中的球队/位置: {exc}")
        return {}

    try:
        resolved_columns = {
            field_name: resolve_column(df, aliases, required=field_name == "uid")
            for field_name, aliases in PLAYER_TEAM_MAP_COLUMN_ALIASES.items()
        }
    except KeyError as exc:
        summary.add_warning(f"{WORKBOOK_SHEET_PLAYER_TEAM_MAP} 缺少关键列，跳过映射回退: {exc}")
        return {}

    overrides: dict[int, dict[str, str]] = {}
    duplicate_uids: set[int] = set()
    for row_index, row in df.iterrows():
        uid_value = row.get(resolved_columns["uid"])
        if is_blank(uid_value):
            continue
        try:
            uid = parse_int(uid_value, "UID")
        except ValueError:
            continue

        override = {
            "team_name": clean_string(row.get(resolved_columns.get("team_name"))),
            "position": clean_string(row.get(resolved_columns.get("position"))),
        }
        if not override["team_name"] and not override["position"]:
            continue
        if uid in overrides:
            duplicate_uids.add(uid)
        overrides[uid] = override

    if duplicate_uids:
        summary.add_warning(f"{WORKBOOK_SHEET_PLAYER_TEAM_MAP} 中存在重复 UID，已按最后一条记录覆盖: {sorted(duplicate_uids)[:10]}")
    summary.details["player_team_overrides"] = len(overrides)
    return overrides
