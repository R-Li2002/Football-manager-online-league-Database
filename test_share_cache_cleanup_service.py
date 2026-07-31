import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from services.share_cache_cleanup_service import cleanup_share_cache


class ShareCacheCleanupServiceTests(unittest.TestCase):
    def test_removes_only_expired_png_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "share-cache"
            nested = root / "player"
            nested.mkdir(parents=True)
            old_png = nested / "old.png"
            new_png = nested / "new.png"
            old_svg = nested / "old.svg"
            old_png.write_bytes(b"old-png")
            new_png.write_bytes(b"new-png")
            old_svg.write_bytes(b"old-svg")

            now = time.time()
            old_time = now - 31 * 24 * 60 * 60
            os.utime(old_png, (old_time, old_time))
            os.utime(old_svg, (old_time, old_time))

            result = cleanup_share_cache(root, retention_days=30, now=now)

            self.assertEqual(result.scanned_files, 2)
            self.assertEqual(result.removed_files, 1)
            self.assertEqual(result.released_bytes, len(b"old-png"))
            self.assertFalse(old_png.exists())
            self.assertTrue(new_png.exists())
            self.assertTrue(old_svg.exists())

    def test_dry_run_does_not_remove_expired_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "share-cache"
            root.mkdir()
            old_png = root / "old.png"
            old_png.write_bytes(b"png")
            now = time.time()
            old_time = now - 31 * 24 * 60 * 60
            os.utime(old_png, (old_time, old_time))

            result = cleanup_share_cache(root, retention_days=30, now=now, dry_run=True)

            self.assertEqual(result.removed_files, 1)
            self.assertTrue(old_png.exists())

    def test_rejects_dangerous_or_unrelated_roots(self):
        for root in ("/", "/app", "/app/data", "/tmp/images"):
            with self.subTest(root=root):
                with self.assertRaises(ValueError):
                    cleanup_share_cache(root)


if __name__ == "__main__":
    unittest.main()
