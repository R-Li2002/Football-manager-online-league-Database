import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from services.share_png_service import SharePngRenderer
from test_internal_share_page import _sample_player_detail, _sample_team_info, _sample_team_players, _sample_wage_detail


class SharePngRendererTests(unittest.TestCase):
    def test_render_player_png_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SharePngRenderer(temp_dir, template_version=2)

            with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"png-bytes")):
                rendered = renderer.render_player_png(
                    _sample_player_detail(),
                    version="2026-03",
                    step=0,
                    theme="dark",
                )

            self.assertEqual(rendered.cache_status, "MISS")
            self.assertTrue(Path(rendered.file_path).exists())
            self.assertEqual(Path(rendered.file_path).read_bytes(), b"png-bytes")

    def test_render_player_png_uses_existing_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SharePngRenderer(temp_dir, template_version=2)
            target = next((Path(temp_dir) / "player").glob("*.png"), None)
            self.assertIsNone(target)

            with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"png-bytes")):
                first = renderer.render_player_png(_sample_player_detail(), version="2026-03", step=0, theme="dark")
                second = renderer.render_player_png(_sample_player_detail(), version="2026-03", step=0, theme="dark")

            self.assertEqual(first.cache_status, "MISS")
            self.assertEqual(second.cache_status, "HIT")
            self.assertEqual(Path(second.file_path).read_bytes(), b"png-bytes")

    def test_render_wage_png_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SharePngRenderer(temp_dir, template_version=2)

            with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"wage-png")):
                rendered = renderer.render_wage_png(_sample_player_detail(), _sample_wage_detail(), theme="dark")

            self.assertEqual(rendered.cache_status, "MISS")
            self.assertEqual(Path(rendered.file_path).read_bytes(), b"wage-png")

    def test_render_roster_png_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = SharePngRenderer(temp_dir, template_version=2)

            with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"roster-png")):
                rendered = renderer.render_roster_png(
                    "Barcelona",
                    _sample_team_players(),
                    team_info=_sample_team_info(),
                    page=1,
                    theme="dark",
                )

            self.assertEqual(rendered.cache_status, "MISS")
            self.assertEqual(Path(rendered.file_path).read_bytes(), b"roster-png")
