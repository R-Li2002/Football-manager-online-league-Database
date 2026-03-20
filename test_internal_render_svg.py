import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.frontend_routes import build_frontend_router
from test_internal_share_page import _dummy_db, _sample_player_detail


class InternalRenderSvgTests(unittest.TestCase):
    def test_internal_render_svg_returns_svg(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
            response = client.get(
                "/internal/render/player/24048100.svg?version=2026-03&step=2",
                headers={"X-Internal-Share-Token": "share-secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/svg+xml")
        self.assertIn("<svg", response.text)
        self.assertIn("Dani Olmo", response.text)

    def test_internal_render_svg_requires_token(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        response = client.get("/internal/render/player/24048100.svg")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "internal_share_token_required")

    def test_internal_render_svg_returns_503_when_token_not_configured(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db))
        client = TestClient(app)

        response = client.get("/internal/render/player/24048100.svg")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "internal_share_not_configured")

    def test_internal_render_svg_returns_404_when_player_missing(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=None):
            response = client.get(
                "/internal/render/player/24048100.svg",
                headers={"X-Internal-Share-Token": "share-secret"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "player_not_found")
