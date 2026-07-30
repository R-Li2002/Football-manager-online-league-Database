import asyncio
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from services import import_upload_service


class ImportUploadServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(os.environ, {"HEIGO_IMPORT_ROOT": self.temp_dir.name})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def _upload(self, filename: str, content: bytes) -> UploadFile:
        return UploadFile(filename=filename, file=BytesIO(content))

    def test_roster_upload_uses_safe_persistent_filename(self):
        path = asyncio.run(
            import_upload_service.save_import_upload(
                self._upload("2630 HEIGO 名单.xlsx", b"PK\x03\x04workbook"),
                "roster",
            )
        )
        self.assertTrue(path.exists())
        self.assertEqual(path.parent, Path(self.temp_dir.name).resolve())
        self.assertIn("2630_HEIGO_名单", path.name)

    def test_schedule_upload_is_stored_in_schedule_directory(self):
        path = asyncio.run(
            import_upload_service.save_import_upload(
                self._upload("87届赛程.xlsm", b"PK\x03\x04schedule"),
                "schedule",
            )
        )
        self.assertEqual(path.parent, (Path(self.temp_dir.name) / "schedules").resolve())

    def test_invalid_extension_and_excel_content_are_rejected(self):
        with self.assertRaises(HTTPException) as extension_error:
            asyncio.run(import_upload_service.save_import_upload(self._upload("名单.txt", b"data"), "roster"))
        self.assertEqual(extension_error.exception.status_code, 400)

        with self.assertRaises(HTTPException) as content_error:
            asyncio.run(import_upload_service.save_import_upload(self._upload("名单.xlsx", b"not-a-zip"), "roster"))
        self.assertEqual(content_error.exception.status_code, 400)

    def test_upload_size_limit_is_enforced(self):
        rules = dict(import_upload_service.UPLOAD_RULES)
        rules["roster"] = ({".xlsx"}, 4, Path("."))
        with patch.object(import_upload_service, "UPLOAD_RULES", rules):
            with self.assertRaises(HTTPException) as size_error:
                asyncio.run(import_upload_service.save_import_upload(self._upload("名单.xlsx", b"PK123"), "roster"))
        self.assertEqual(size_error.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
