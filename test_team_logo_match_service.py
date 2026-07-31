import unittest
import io
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile
from starlette.datastructures import Headers, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Team, TeamLogoSource
from schemas_write import TeamLogoMatchApplyRequest
from services import team_logo_match_service as service


SAFE_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/></linearGradient></defs><path fill="url(#g)" d="M0 0h100v100H0z"/></svg>'''


class TeamLogoMatchServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(Team(id=7, name="R. Madrid", level="超级", logo_path="/old.png"))
        self.db.commit()
        service.SEARCH_CACHE.clear()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_search_sorts_color_candidate_first(self):
        upstream = [
            {"slug": "/rfef/club/Real-Madrid-CF-v2002-mono", "version": 2002, "preview_image_url": "https://cdn.sanity.io/images/x/mono.png", "style_name": "Mono", "subject_name": "Real Madrid Club de Futbol", "subject_short_name": "Real Madrid"},
            {"slug": "/rfef/club/Real-Madrid-CF-v2002", "version": 2002, "preview_image_url": "https://cdn.sanity.io/images/x/color.png", "style_name": "Color", "subject_name": "Real Madrid Club de Futbol", "subject_short_name": "Real Madrid"},
        ]
        with mock.patch.object(service, "_fetch_json", return_value=upstream):
            result = service.search_fclogo(self.db, "admin", 7, "R. Madrid")
        self.assertEqual(result["candidates"][0]["variant"], "Color")
        self.assertGreater(result["candidates"][0]["confidence"], result["candidates"][1]["confidence"])

    def test_slug_validation_blocks_external_and_traversal_values(self):
        for value in ["https://evil.example/logo", "//evil.example/logo", "/club/../secret", "club/logo"]:
            with self.subTest(value=value), self.assertRaises(HTTPException):
                service._asset_url_for_slug(value)

    def test_detail_page_preserves_case_sensitive_asset_filename(self):
        html = '<meta property="og:image" content="https://assets.fclogo.top/png/Feyenoord-Rotterdam-v2024.png">'
        self.assertEqual(
            service._asset_url_from_detail_html(html),
            "https://assets.fclogo.top/svg/Feyenoord-Rotterdam-v2024.svg",
        )

    def test_svg_sanitizer_removes_scripts_events_and_external_links(self):
        unsafe = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="alert(1)"><script>alert(1)</script><a href="https://evil.example"><path style="fill:url(relative.svg)" d="M0 0h1v1z"/></a><path fill="url(#safe)" d="M0 0h2v2z"/></svg>'''
        cleaned = service.sanitize_svg(unsafe).decode("utf-8")
        self.assertNotIn("script", cleaned.lower())
        self.assertNotIn("onload", cleaned.lower())
        self.assertNotIn("https://evil.example", cleaned)
        self.assertNotIn("relative.svg", cleaned)
        self.assertIn("url(#safe)", cleaned)

    def test_svg_sanitizer_rejects_doctype(self):
        with self.assertRaises(HTTPException):
            service.sanitize_svg(b'<!DOCTYPE svg><svg viewBox="0 0 1 1"></svg>')

    def test_apply_requires_explicit_confirmation(self):
        request = TeamLogoMatchApplyRequest(team_id=7, slug="/rfef/club/Real-Madrid", matched_query="Real Madrid", source_name="Real Madrid", confirmed=False)
        with self.assertRaises(HTTPException):
            service.apply_fclogo_candidate(self.db, "admin", request, mock.Mock())
        self.assertEqual(self.db.get(Team, 7).logo_path, "/old.png")

    def test_apply_saves_derivatives_and_source_record(self):
        request = TeamLogoMatchApplyRequest(
            team_id=7,
            slug="/rfef/club/Real-Madrid-CF-v2002",
            matched_query="Real Madrid",
            source_name="Real Madrid Club de Futbol",
            source_version="2002",
            source_variant="Color",
            matched_score=100,
            confirmed=True,
        )
        with TemporaryDirectory() as temp_dir, \
             mock.patch.object(service, "TEAM_LOGO_ROOT", Path(temp_dir)), \
             mock.patch.object(service, "_resolve_asset_url", return_value="https://assets.fclogo.top/svg/Real-Madrid-CF-v2002.svg"), \
             mock.patch.object(service, "_fetch_bytes", return_value=SAFE_SVG), \
             mock.patch.object(service, "_render_webp", side_effect=lambda _svg, target: target.write_bytes(b"webp")), \
             mock.patch.object(service, "_delete_previous_team_logo"):
            result = service.apply_fclogo_candidate(self.db, "admin", request, mock.Mock())
            self.assertTrue((Path(temp_dir) / Path(result["logo_path"]).name).exists())
            self.assertTrue(any(path.suffix == ".svg" for path in Path(temp_dir).iterdir()))
        source = self.db.query(TeamLogoSource).filter(TeamLogoSource.team_id == 7).one()
        self.assertEqual(source.provider, "fclogo")
        self.assertEqual(source.source_variant, "Color")
        self.assertEqual(self.db.get(Team, 7).logo_path, result["logo_path"])

    def test_local_svg_upload_is_sanitized_and_recorded_as_a_source(self):
        upload = UploadFile(
            filename="custom-crest.svg",
            file=io.BytesIO(SAFE_SVG),
            headers=Headers({"content-type": "image/svg+xml"}),
        )
        with TemporaryDirectory() as temp_dir, \
             mock.patch.object(service, "TEAM_LOGO_ROOT", Path(temp_dir)), \
             mock.patch.object(service, "_render_webp", side_effect=lambda _svg, target: target.write_bytes(b"webp")), \
             mock.patch.object(service, "_delete_previous_team_logo"):
            result = service.upload_local_team_logo(self.db, "admin", 7, upload, mock.Mock(), confirmed=True)
            self.assertTrue(any(path.suffix == ".svg" for path in Path(temp_dir).iterdir()))
            self.assertTrue(any(path.suffix == ".webp" for path in Path(temp_dir).iterdir()))
        source = self.db.query(TeamLogoSource).filter(TeamLogoSource.team_id == 7).one()
        self.assertEqual(source.provider, "local_upload")
        self.assertEqual(source.source_name, "custom-crest.svg")
        self.assertEqual(result["source"]["source_variant"], "SVG")

if __name__ == "__main__":
    unittest.main()
