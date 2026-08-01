#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import SessionLocal
from services.ranking_import_service import import_ranking_workbook, preview_ranking_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or import the HEIGO ranking workbook.")
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        report = (
            import_ranking_workbook(db, args.workbook, force=args.force)
            if args.execute
            else preview_ranking_workbook(db, args.workbook)
        )
        print(json.dumps({"executed": args.execute, **report}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
