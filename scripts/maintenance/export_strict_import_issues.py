from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from import_data import (
    ATTRIBUTE_COLUMN_ALIASES,
    PLAYER_COLUMN_ALIASES,
    PLAYER_TEAM_MAP_COLUMN_ALIASES,
    TEAM_COLUMN_ALIASES,
    TEAM_NAME_ALIASES,
    WORKBOOK_SHEET_LEAGUE_PLAYERS,
    WORKBOOK_SHEET_OVERVIEW,
    WORKBOOK_SHEET_PLAYER_TEAM_MAP,
    choose_latest_file,
    clean_string,
    normalize_team_identifier,
    resolve_column,
    resolve_input_files,
    resolve_sheet_name,
    run_import,
)


def load_frame(workbook_path: Path, sheet_name: str, header: int | None) -> pd.DataFrame:
    resolved_sheet_name = resolve_sheet_name(workbook_path, sheet_name)
    return pd.read_excel(workbook_path, sheet_name=resolved_sheet_name, header=header, dtype=object)


def canonical_team_name(raw_value: Any, canonical_team_names: set[str], normalized_team_names: dict[str, str]) -> tuple[str, str]:
    team_name = clean_string(raw_value)
    if not team_name:
        return "", ""
    if team_name in canonical_team_names:
        return team_name, "exact"

    alias_match = TEAM_NAME_ALIASES.get(team_name, "")
    if alias_match in canonical_team_names:
        return alias_match, "alias_map"

    normalized_match = normalized_team_names.get(normalize_team_identifier(team_name), "")
    if normalized_match in canonical_team_names:
        return normalized_match, "normalized_match"

    return "", ""


def parse_player_issue(message: str) -> tuple[str, int | None, int | None]:
    if not message.startswith("Excel 行 "):
        return "other", None, None

    try:
        row_part, detail_part = message.split(": ", 1)
        excel_row = int(row_part.replace("Excel 行 ", ""))
    except (ValueError, IndexError):
        return "other", None, None

    uid = None
    if "UID " in detail_part:
        uid_part = detail_part.split("UID ", 1)[1]
        uid_text = uid_part.split(" ", 1)[0]
        try:
            uid = int(uid_text)
        except ValueError:
            uid = None

    if "缺少位置" in detail_part:
        return "missing_position", excel_row, uid
    if "缺少球队" in detail_part:
        return "missing_team", excel_row, uid
    if "球队不存在" in detail_part:
        return "team_name_mismatch", excel_row, uid
    if "UID 重复" in detail_part:
        return "duplicate_uid", excel_row, uid
    return "other", excel_row, uid


def load_optional_mapping(workbook_path: Path) -> tuple[dict[int, dict[str, str]], str]:
    try:
        df = load_frame(workbook_path, WORKBOOK_SHEET_PLAYER_TEAM_MAP, header=0)
    except Exception:
        return {}, "missing"

    try:
        uid_col = resolve_column(df, PLAYER_TEAM_MAP_COLUMN_ALIASES["uid"])
        team_col = resolve_column(df, PLAYER_TEAM_MAP_COLUMN_ALIASES["team_name"], required=False)
        position_col = resolve_column(df, PLAYER_TEAM_MAP_COLUMN_ALIASES["position"], required=False)
    except KeyError:
        return {}, "invalid"

    mapping: dict[int, dict[str, str]] = {}
    for _, row in df.iterrows():
        uid_value = row.get(uid_col)
        if pd.isna(uid_value):
            continue
        try:
            uid = int(float(str(uid_value)))
        except (TypeError, ValueError):
            continue
        mapping[uid] = {
            "team_name": clean_string(row.get(team_col)) if team_col else "",
            "position": clean_string(row.get(position_col)) if position_col else "",
        }
    return mapping, "loaded"


def load_attribute_lookup(attributes_csv_path: Path) -> dict[int, dict[str, str]]:
    df = pd.read_csv(attributes_csv_path, dtype=object, low_memory=False)
    uid_col = resolve_column(df, ATTRIBUTE_COLUMN_ALIASES["uid"])
    position_col = resolve_column(df, ATTRIBUTE_COLUMN_ALIASES["position"], required=False)
    club_col = resolve_column(df, ATTRIBUTE_COLUMN_ALIASES["club"], required=False)

    lookup: dict[int, dict[str, str]] = {}
    for _, row in df.iterrows():
        uid_value = row.get(uid_col)
        if pd.isna(uid_value):
            continue
        try:
            uid = int(float(str(uid_value)))
        except (TypeError, ValueError):
            continue
        lookup[uid] = {
            "position": clean_string(row.get(position_col)) if position_col else "",
            "club": clean_string(row.get(club_col)) if club_col else "",
        }
    return lookup


def build_issue_rows(workbook_path: Path, attributes_csv_path: Path, root_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report = run_import(
        workbook_path=workbook_path,
        attributes_csv_path=attributes_csv_path,
        dry_run=True,
        strict_mode=True,
        root_dir=root_dir,
    )
    if report.fatal_error:
        raise RuntimeError(report.fatal_error)

    player_summary = report.datasets.get("players")
    if player_summary is None:
        return [], {"has_errors": False, "error_counts": {}}

    league_df = load_frame(workbook_path, WORKBOOK_SHEET_LEAGUE_PLAYERS, header=0)
    resolved_columns = {
        field_name: resolve_column(league_df, aliases, required=field_name in {"uid", "name", "age", "ca", "pa", "position", "team_name"})
        for field_name, aliases in PLAYER_COLUMN_ALIASES.items()
    }
    team_source_col = resolved_columns["team_name"]
    team_source_label = f"联赛名单.{clean_string(team_source_col)}"
    club_team_col = resolve_column(league_df, ["俱乐部"], required=False)

    overview_df = load_frame(workbook_path, WORKBOOK_SHEET_OVERVIEW, header=1)
    overview_team_col = resolve_column(overview_df, TEAM_COLUMN_ALIASES["name"])
    canonical_team_names = {
        clean_string(value)
        for value in overview_df[overview_team_col].tolist()
        if clean_string(value)
    }
    normalized_team_names = {
        normalize_team_identifier(team_name): team_name for team_name in canonical_team_names
    }

    mapping_lookup, mapping_status = load_optional_mapping(workbook_path)
    attribute_lookup = load_attribute_lookup(attributes_csv_path)

    issue_rows: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()

    for message in player_summary.errors:
        issue_type, excel_row, uid = parse_player_issue(message)
        issue_counter[issue_type] += 1
        if excel_row is None or excel_row < 2:
            continue

        frame_index = excel_row - 2
        if frame_index >= len(league_df):
            continue

        row = league_df.iloc[frame_index]
        uid_value = uid or clean_string(row.get(resolved_columns["uid"]))
        player_name = clean_string(row.get(resolved_columns["name"]))
        raw_position = clean_string(row.get(resolved_columns["position"]))
        raw_club_name = clean_string(row.get(club_team_col)) if club_team_col else ""
        raw_team_source_value = clean_string(row.get(team_source_col))

        mapping_record = mapping_lookup.get(uid or -1, {})
        attribute_record = attribute_lookup.get(uid or -1, {})

        suggested_position = ""
        suggested_position_basis = ""
        if issue_type == "missing_position":
            if clean_string(mapping_record.get("position")):
                suggested_position = clean_string(mapping_record["position"])
                suggested_position_basis = "球员对应球队(参考)"
            elif clean_string(attribute_record.get("position")):
                suggested_position = clean_string(attribute_record["position"])
                suggested_position_basis = "球员属性.csv"

        suggested_team_name = ""
        suggested_team_basis = ""
        for basis_label, candidate_value in [
            (team_source_label, raw_team_source_value),
            ("联赛名单.俱乐部", raw_club_name),
            ("球员对应球队(参考)", clean_string(mapping_record.get("team_name"))),
            ("球员属性.俱乐部(参考)", clean_string(attribute_record.get("club"))),
        ]:
            candidate_team_name, basis = canonical_team_name(candidate_value, canonical_team_names, normalized_team_names)
            if candidate_team_name:
                suggested_team_name = candidate_team_name
                suggested_team_basis = f"{basis_label} ({basis})"
                break

        if issue_type == "missing_position":
            suggested_action = (
                f"将 联赛名单.位置 补为 {suggested_position}"
                if suggested_position
                else "需人工补齐 联赛名单.位置"
            )
        elif issue_type in {"missing_team", "team_name_mismatch"}:
            suggested_action = (
                f"将 {team_source_label} 统一为 {suggested_team_name}"
                if suggested_team_name
                else "需人工核对球队归属，并统一为 信息总览.球队名"
            )
        else:
            suggested_action = "需人工核对该条记录"

        issue_rows.append(
            {
                "问题类型": issue_type,
                "Excel行": excel_row,
                "UID": uid_value,
                "姓名": player_name,
                "联赛名单.位置": raw_position,
                "联赛名单.球队来源列": clean_string(team_source_col),
                "联赛名单.球队来源值": raw_team_source_value,
                "联赛名单.俱乐部": raw_club_name,
                "球员对应球队.球队(参考)": clean_string(mapping_record.get("team_name")),
                "球员对应球队.位置(参考)": clean_string(mapping_record.get("position")),
                "球员属性.俱乐部(参考)": clean_string(attribute_record.get("club")),
                "球员属性.位置(参考)": clean_string(attribute_record.get("position")),
                "建议规范球队名": suggested_team_name,
                "建议球队依据": suggested_team_basis,
                "建议位置": suggested_position,
                "建议位置依据": suggested_position_basis,
                "建议修复动作": suggested_action,
                "严格模式错误": message,
            }
        )

    issue_rows.sort(key=lambda item: (item["问题类型"], int(item["Excel行"]), str(item["UID"])))
    summary = {
        "has_errors": report.has_errors,
        "player_error_counts": dict(issue_counter),
        "player_created": player_summary.created,
        "player_skipped": player_summary.skipped,
        "mapping_sheet_status": mapping_status,
        "canonical_team_count": len(canonical_team_names),
        "strict_rules": {
            "position": "联赛名单.位置 必须非空",
            "team_name": "联赛名单中的球队名必须与 信息总览.球队名 完全一致",
        },
    }
    return issue_rows, summary


def write_issue_workbook(
    issue_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    workbook_path: Path,
    attributes_csv_path: Path,
    output_xlsx: Path,
    output_csv: Path,
) -> None:
    summary_rows = [
        {"项目": "生成时间", "值": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        {"项目": "工作簿", "值": str(workbook_path)},
        {"项目": "属性CSV", "值": str(attributes_csv_path)},
        {"项目": "严格模式有错误", "值": summary["has_errors"]},
        {"项目": "问题总数", "值": len(issue_rows)},
        {"项目": "规范球队数", "值": summary["canonical_team_count"]},
        {"项目": "映射表状态", "值": summary["mapping_sheet_status"]},
    ]
    for issue_type, count in summary["player_error_counts"].items():
        summary_rows.append({"项目": f"错误计数.{issue_type}", "值": count})
    for key, value in summary["strict_rules"].items():
        summary_rows.append({"项目": f"严格规则.{key}", "值": value})

    issues_df = pd.DataFrame(issue_rows)
    summary_df = pd.DataFrame(summary_rows)

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        issues_df.to_excel(writer, sheet_name="PlayerIssues", index=False)

        workbook_sheet = writer.book["PlayerIssues"]
        workbook_sheet.freeze_panes = "A2"
        for column_cells in workbook_sheet.columns:
            values = [len(str(cell.value)) for cell in column_cells if cell.value is not None]
            max_length = max(values, default=10)
            workbook_sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 40)

    issues_df.to_csv(output_csv, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出 HEIGO 严格模式导入错误清单")
    parser.add_argument("--workbook", type=str, help="联机联赛 Excel 路径")
    parser.add_argument("--attributes-csv", type=str, help="球员属性 CSV 路径")
    parser.add_argument("--output-xlsx", type=str, help="输出 Excel 清单路径；默认自动使用时间戳命名")
    parser.add_argument("--output-csv", type=str, help="输出 CSV 清单路径；默认自动使用时间戳命名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    workbook_path, attributes_csv_path, _warnings = resolve_input_files(args.workbook, args.attributes_csv, root_dir)
    issue_rows, summary = build_issue_rows(workbook_path, attributes_csv_path, root_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_xlsx = Path(args.output_xlsx) if args.output_xlsx else Path(f"strict_import_issue_list_{timestamp}.xlsx")
    output_csv = Path(args.output_csv) if args.output_csv else Path(f"strict_import_issue_list_{timestamp}.csv")
    if not output_xlsx.is_absolute():
        output_xlsx = root_dir / output_xlsx
    if not output_csv.is_absolute():
        output_csv = root_dir / output_csv

    write_issue_workbook(issue_rows, summary, workbook_path, attributes_csv_path, output_xlsx, output_csv)
    print(f"Exported {len(issue_rows)} issues to {output_xlsx}")
    print(f"CSV copy written to {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
