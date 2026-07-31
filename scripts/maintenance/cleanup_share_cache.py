from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.share_cache_cleanup_service import cleanup_share_cache


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely clean expired HEIGO share PNG cache files.")
    parser.add_argument("--cache-root", default="data/share-cache")
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--execute", action="store_true", help="Delete files; otherwise only report candidates.")
    args = parser.parse_args()

    result = cleanup_share_cache(
        args.cache_root,
        retention_days=args.retention_days,
        dry_run=not args.execute,
    )
    mode = "execute" if args.execute else "dry-run"
    print(
        f"mode={mode} scanned={result.scanned_files} candidates={result.removed_files} "
        f"releasable_bytes={result.released_bytes} retention_days={args.retention_days}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
