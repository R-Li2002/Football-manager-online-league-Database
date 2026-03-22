import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.frontend_routes import build_frontend_router
from services import share_signature_service
from test_internal_share_page import _dummy_db, _sample_player_detail, _sample_team_info, _sample_team_players, _sample_wage_detail


def _build_player_signature(uid: int, *, version: str | None = None, step: int = 0, theme: str = "dark", exp: int) -> str:
    return share_signature_service.sign_player_render_request(
        "render-secret",
        uid=uid,
        version=version,
        step=step,
        theme=theme,
        exp=exp,
    )


def _build_wage_signature(uid: int, *, theme: str = "dark", exp: int) -> str:
    return share_signature_service.sign_wage_render_request(
        "render-secret",
        uid=uid,
        theme=theme,
        exp=exp,
    )


def _build_roster_signature(team_name: str, *, page: int = 1, theme: str = "dark", exp: int) -> str:
    return share_signature_service.sign_roster_render_request(
        "render-secret",
        team_name=team_name,
        page=page,
        theme=theme,
        exp=exp,
    )


class InternalRenderPngTests(unittest.TestCase):
    def test_internal_render_png_returns_png(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(
                build_frontend_router(
                    _dummy_db,
                    internal_share_token="share-secret",
                    internal_render_signing_key="render-secret",
                    share_cache_root=temp_dir,
                )
            )
            client = TestClient(app)
            exp = int(time.time()) + 60
            sig = _build_player_signature(24048100, version="2026-03", exp=exp)

            with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
                with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"png-bytes")):
                    response = client.get(
                        f"/internal/render/player/24048100.png?version=2026-03&step=0&theme=dark&exp={exp}&sig={sig}"
                    )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["x-render-cache"], "MISS")
        self.assertEqual(response.content, b"png-bytes")

    def test_internal_render_wage_png_returns_png(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60
            sig = _build_wage_signature(24048100, exp=exp)

            with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
                with patch("routers.frontend_routes.read_service.get_player_wage_detail", return_value=_sample_wage_detail()):
                    with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"wage-png")):
                        response = client.get(f"/internal/render/wage/24048100.png?theme=dark&exp={exp}&sig={sig}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"wage-png")

    def test_internal_render_roster_png_returns_png(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60
            sig = _build_roster_signature("Barcelona", page=1, exp=exp)

            with patch("routers.frontend_routes.read_service.get_players_by_team", return_value=_sample_team_players()):
                with patch("routers.frontend_routes.read_service.get_team_info", return_value=_sample_team_info()):
                    with patch("services.share_png_service.cairosvg", new=SimpleNamespace(svg2png=lambda **_: b"roster-png")):
                        response = client.get(f"/internal/render/roster.png?team=Barcelona&page=1&theme=dark&exp={exp}&sig={sig}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"roster-png")

    def test_internal_render_png_rejects_invalid_signature(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60

            response = client.get(f"/internal/render/player/24048100.png?version=2026-03&step=0&theme=dark&exp={exp}&sig=bad")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "invalid_signature")

    def test_internal_render_png_rejects_expired_url(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) - 1
            sig = _build_player_signature(24048100, version="2026-03", exp=exp)

            response = client.get(f"/internal/render/player/24048100.png?version=2026-03&step=0&theme=dark&exp={exp}&sig={sig}")

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["detail"], "render_url_expired")

    def test_internal_render_png_returns_404_when_player_missing(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60
            sig = _build_player_signature(24048100, version="2026-03", exp=exp)

            with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=None):
                response = client.get(f"/internal/render/player/24048100.png?version=2026-03&step=0&theme=dark&exp={exp}&sig={sig}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "player_not_found")

    def test_internal_render_roster_png_returns_404_when_team_missing(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, internal_render_signing_key="render-secret", share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60
            sig = _build_roster_signature("Barcelona", page=1, exp=exp)

            with patch("routers.frontend_routes.read_service.get_players_by_team", return_value=[]):
                response = client.get(f"/internal/render/roster.png?team=Barcelona&page=1&theme=dark&exp={exp}&sig={sig}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "team_not_found")

    def test_internal_render_png_returns_503_when_signing_key_not_configured(self):
        app = FastAPI()
        with tempfile.TemporaryDirectory() as temp_dir:
            app.include_router(build_frontend_router(_dummy_db, share_cache_root=temp_dir))
            client = TestClient(app)
            exp = int(time.time()) + 60

            response = client.get(f"/internal/render/player/24048100.png?version=2026-03&step=0&theme=dark&exp={exp}&sig=anything")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "internal_render_not_configured")
