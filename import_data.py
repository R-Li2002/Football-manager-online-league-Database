from __future__ import annotations

import argparse
import json
from pathlib import Path

from imports_runtime.attribute_parser import decode_player_habit_value
from imports_runtime.constants import (
    ATTRIBUTE_COLUMN_ALIASES,
    DEFAULT_LEAGUE_INFO_VALUES,
    HIDDEN_SEA_TEAM_LEVEL,
    HIDDEN_SEA_TEAM_NAME,
    PLAYER_COLUMN_ALIASES,
    PLAYER_TEAM_MAP_COLUMN_ALIASES,
    TEAM_COLUMN_ALIASES,
    TEAM_NAME_ALIASES,
    WORKBOOK_SHEET_LEAGUE_PLAYERS,
    WORKBOOK_SHEET_OVERVIEW,
    WORKBOOK_SHEET_PLAYER_TEAM_MAP,
)
from imports_runtime.persistence import run_import
from imports_runtime.reporting import DatasetSummary, ImportReport, print_report
from imports_runtime.source_resolver import choose_latest_file, resolve_input_files
from imports_runtime.validators import clean_string, normalize_team_identifier, resolve_column
from imports_runtime.workbook_parser import resolve_sheet_name


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HEIGO 联机联赛数据库导入工具")
    parser.add_argument("--workbook", type=str, help="联机联赛 Excel 文件路径")
    parser.add_argument("--attributes-csv", type=str, help="球员属性 CSV 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只校验和预演导入，不提交数据库变更")
    parser.add_argument("--report-json", type=str, help="将导入报告输出到 JSON 文件")
    parser.add_argument("--seed-admin", action="store_true", help="额外创建 legacy admin 账户（默认不启用）")
    parser.add_argument("--admin-username", type=str, default="admin", help="legacy admin 用户名")
    parser.add_argument("--admin-password", type=str, default="heigo85", help="legacy admin 密码")
    parser.add_argument("--allow-legacy-fallback", action="store_true", help="允许使用球员对应球队、队名别名和俱乐部回退等兼容导入逻辑")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    report = run_import(
        workbook_path=args.workbook,
        attributes_csv_path=args.attributes_csv,
        dry_run=args.dry_run,
        seed_admin=args.seed_admin,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
        strict_mode=not args.allow_legacy_fallback,
    )
    print_report(report)

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON report written to: {report_path}")

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
