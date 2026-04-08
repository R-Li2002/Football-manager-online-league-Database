from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database import SessionLocal
from imports_runtime.constants import HIDDEN_SEA_TEAM_LEVEL, TEAM_COLUMN_ALIASES, TEAM_NAME_ALIASES, WORKBOOK_SHEET_OVERVIEW
from imports_runtime.validators import clean_string, normalize_team_identifier, resolve_column
from imports_runtime.workbook_parser import load_excel
from models import Player, Team
from repositories.player_repository import get_team_players
from repositories.team_repository import get_other_team_by_name, get_team_by_name, list_visible_teams

SCRIPT_OPERATOR = "maintenance.rename_teams_from_workbook"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or apply batch team renames based on a league workbook.")
    parser.add_argument("--workbook", required=True, help="Path to the league workbook (.xlsx).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the rename plan. Without this flag the script only prints a preview.",
    )
    parser.add_argument(
        "--mapping-json",
        help="Optional JSON file containing explicit old->new mappings. When provided it overrides workbook auto-matching.",
    )
    return parser


def load_workbook_team_names(workbook_path: Path) -> list[str]:
    df = load_excel(workbook_path, WORKBOOK_SHEET_OVERVIEW, header=1)
    team_name_column = resolve_column(df, TEAM_COLUMN_ALIASES["name"])
    level_column = resolve_column(df, TEAM_COLUMN_ALIASES["level"])

    team_names: list[str] = []
    seen_names: set[str] = set()
    for _, row in df.iterrows():
        team_name = clean_string(row.get(team_name_column))
        level = clean_string(row.get(level_column))
        if not team_name and not level:
            continue
        if not team_name or team_name in seen_names:
            continue
        seen_names.add(team_name)
        team_names.append(team_name)
    return team_names


def load_json_mapping(mapping_path: Path) -> dict[str, str]:
    payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_items = payload.items()
    elif isinstance(payload, list):
        raw_items = []
        for item in payload:
            if not isinstance(item, dict) or "old" not in item or "new" not in item:
                raise ValueError("JSON list items must contain 'old' and 'new' keys.")
            raw_items.append((item["old"], item["new"]))
    else:
        raise ValueError("JSON mapping must be an object or a list of {'old','new'} items.")

    mapping: dict[str, str] = {}
    for old_name, new_name in raw_items:
        old_text = clean_string(old_name)
        new_text = clean_string(new_name)
        if not old_text or not new_text:
            raise ValueError("Mapping entries cannot be blank.")
        mapping[old_text] = new_text
    return mapping


def build_auto_mapping(db_team_names: Iterable[str], workbook_team_names: Iterable[str]) -> dict[str, str]:
    db_team_list = list(db_team_names)
    db_team_set = set(db_team_list)
    normalized_db_names = {normalize_team_identifier(team_name): team_name for team_name in db_team_list}
    workbook_team_set = set(workbook_team_names)

    mapping: dict[str, str] = {}
    for workbook_team_name in sorted(workbook_team_set - db_team_set):
        old_name = TEAM_NAME_ALIASES.get(workbook_team_name)
        if not old_name:
            continue
        matched_old_name = old_name if old_name in db_team_set else normalized_db_names.get(normalize_team_identifier(old_name))
        if not matched_old_name:
            continue
        if matched_old_name in workbook_team_set:
            continue
        mapping[matched_old_name] = workbook_team_name
    return mapping


def validate_mapping(mapping: dict[str, str]) -> None:
    targets = list(mapping.values())
    duplicate_targets = sorted({target for target in targets if targets.count(target) > 1})
    if duplicate_targets:
        raise ValueError(f"Multiple source teams target the same new name: {duplicate_targets}")


def apply_team_rename(db, old_name: str, new_name: str) -> dict[str, int | str]:
    team = get_team_by_name(db, old_name)
    if team is None:
        raise ValueError(f"Source team not found: {old_name}")

    existing = get_other_team_by_name(db, new_name, team.id)
    if existing is not None:
        raise ValueError(f"Target team name already exists: {new_name}")

    players = get_team_players(db, team)
    updated_player_count = 0
    for player in players:
        if player.team_name != new_name:
            player.team_name = new_name
        player.team_id = team.id
        updated_player_count += 1

    team.name = new_name
    return {
        "old_name": old_name,
        "new_name": new_name,
        "updated_player_count": updated_player_count,
        "team_id": team.id,
    }


def preview_mapping(db, mapping: dict[str, str]) -> list[dict[str, int | str]]:
    preview_rows: list[dict[str, int | str]] = []
    for old_name, new_name in mapping.items():
        team = get_team_by_name(db, old_name)
        if team is None:
            raise ValueError(f"Source team not found: {old_name}")
        players = get_team_players(db, team)
        preview_rows.append(
            {
                "old_name": old_name,
                "new_name": new_name,
                "updated_player_count": len(players),
                "team_id": team.id,
            }
        )
    return preview_rows


def print_plan(title: str, rows: list[dict[str, int | str]]) -> None:
    print(title)
    if not rows:
        print("  (no matching renames)")
        return
    for row in rows:
        print(
            f"  {row['old_name']} -> {row['new_name']} "
            f"(team_id={row['team_id']}, players={row['updated_player_count']})"
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    workbook_path = Path(args.workbook).expanduser().resolve()
    if not workbook_path.exists():
        raise SystemExit(f"Workbook not found: {workbook_path}")

    db = SessionLocal()
    try:
        visible_db_team_names = [team.name for team in list_visible_teams(db, HIDDEN_SEA_TEAM_LEVEL)]
        if args.mapping_json:
            mapping = load_json_mapping(Path(args.mapping_json).expanduser().resolve())
        else:
            workbook_team_names = load_workbook_team_names(workbook_path)
            mapping = build_auto_mapping(visible_db_team_names, workbook_team_names)

        validate_mapping(mapping)
        plan_rows = preview_mapping(db, mapping)
        print_plan("Rename plan:", plan_rows)

        if not args.apply:
            print("\nPreview only. Re-run with --apply to commit these renames.")
            db.rollback()
            return 0

        applied_rows: list[dict[str, int | str]] = []
        for old_name, new_name in mapping.items():
            applied_rows.append(apply_team_rename(db, old_name, new_name))

        db.commit()
        print_plan("\nApplied renames:", applied_rows)
        print(f"\nDone. operator={SCRIPT_OPERATOR}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Rename failed: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
