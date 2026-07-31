#!/usr/bin/env python3
"""Build the self-hosted HEIGO UI WOFF2 subset from visible project copy."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from fontTools import subset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "static" / "font" / "heigo-pingfang-pro-sc-regular.ttf"
DEFAULT_OUTPUT = ROOT / "static" / "font" / "heigo-ui-cn.woff2"
DEFAULT_DATABASE = ROOT / "data" / "fm_league.db"
SCAN_ROOTS = (ROOT / "static", ROOT / "services", ROOT / "routers")
SCAN_SUFFIXES = {".html", ".js", ".css", ".py"}
DATABASE_TEXT_COLUMNS = {
    "teams": ("name", "manager", "level", "notes"),
    "players": ("name", "position", "nationality", "team_name", "slot_type"),
    "coaches": ("nickname", "team_name", "level", "title", "bio"),
    "coach_honors": ("season", "competition", "honor", "description", "placement"),
    "home_promotions": ("eyebrow", "title", "body", "action_label"),
    "site_notes": ("text",),
    "candidate_lists": ("name", "description"),
    "operation_audits": ("category", "action", "status", "operator", "summary"),
}
BASE_TEXT = """
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789
，。！？：；、“”‘’（）【】《》〈〉·—…+-/%:,.()[]#@_ 
超甲乙级联赛冠军杯联盟无铭剑HEIGO战力CA PA UID QQ Excel
"""


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def collect_database_text(database: Path) -> set[str]:
    characters: set[str] = set()
    if not database.exists():
        return characters

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        available_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for table_name, text_columns in DATABASE_TEXT_COLUMNS.items():
            if table_name not in available_tables:
                continue
            for column_name in text_columns:
                query = (
                    f"SELECT {quote_identifier(column_name)} FROM {quote_identifier(table_name)} "
                    f"WHERE {quote_identifier(column_name)} IS NOT NULL"
                )
                for (value,) in connection.execute(query):
                    characters.update(str(value))
    finally:
        connection.close()
    return characters


def collect_text(database: Path) -> str:
    characters = set(BASE_TEXT)
    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if path.suffix.lower() not in SCAN_SUFFIXES or not path.is_file():
                continue
            try:
                characters.update(path.read_text(encoding="utf-8-sig"))
            except UnicodeDecodeError:
                continue
    characters.update(collect_database_text(database))
    return "".join(sorted(characters))


def build(source: Path, output: Path, database: Path) -> None:
    if not source.exists():
        raise SystemExit(f"Font source not found: {source}")

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    options.name_legacy = True
    options.name_languages = [0x409, 0x804]
    options.recommended_glyphs = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.glyph_names = False
    options.hinting = False

    font = subset.load_font(str(source), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=collect_text(database))
    subsetter.subset(font)
    output.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(output), options)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve(), args.database.resolve())
    print(f"Built {args.output} ({args.output.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
