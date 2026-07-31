from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
import time


LOGGER = logging.getLogger(__name__)
DEFAULT_RETENTION_DAYS = 30
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class ShareCacheCleanupResult:
    scanned_files: int
    removed_files: int
    released_bytes: int


def _resolve_safe_cache_root(cache_root: str | Path) -> Path:
    root = Path(cache_root).expanduser().resolve()
    dangerous_roots = {Path("/").resolve(), Path("/app").resolve(), Path("/app/data").resolve()}
    if root in dangerous_roots or root.name != "share-cache":
        raise ValueError(f"unsafe share cache root: {root}")
    return root


def cleanup_share_cache(
    cache_root: str | Path,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: float | None = None,
    dry_run: bool = False,
) -> ShareCacheCleanupResult:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    root = _resolve_safe_cache_root(cache_root)
    if not root.exists():
        return ShareCacheCleanupResult(0, 0, 0)
    if not root.is_dir():
        raise ValueError(f"share cache root is not a directory: {root}")

    cutoff = (time.time() if now is None else now) - retention_days * 24 * 60 * 60
    scanned_files = 0
    removed_files = 0
    released_bytes = 0

    for path in root.rglob("*.png"):
        if not path.is_file():
            continue
        scanned_files += 1
        stat = path.stat()
        if stat.st_mtime >= cutoff:
            continue
        removed_files += 1
        released_bytes += stat.st_size
        if not dry_run:
            path.unlink()

    return ShareCacheCleanupResult(scanned_files, removed_files, released_bytes)


async def run_share_cache_cleanup_loop(
    cache_root: str | Path,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            result = await asyncio.to_thread(
                cleanup_share_cache,
                cache_root,
                retention_days=retention_days,
            )
            LOGGER.info(
                "share cache cleanup completed: scanned=%s removed=%s released_bytes=%s retention_days=%s",
                result.scanned_files,
                result.removed_files,
                result.released_bytes,
                retention_days,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("share cache cleanup failed")
        await asyncio.sleep(interval_seconds)
