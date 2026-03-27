import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.frontend_routes import build_frontend_router
from test_internal_share_page import _dummy_db, _sample_player_detail, _sample_team_info, _sample_team_players, _sample_wage_detail


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
        self.assertIn("Noto Sans CJK SC", response.text)
        self.assertIn("HEIGO 球员详情图", response.text)
        self.assertIn("位置熟练度图", response.text)
        self.assertNotIn("#ff9fbe", response.text)

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

    def test_internal_render_wage_svg_returns_svg(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_player_attribute_detail", return_value=_sample_player_detail()):
            with patch("routers.frontend_routes.read_service.get_player_wage_detail", return_value=_sample_wage_detail()):
                response = client.get(
                    "/internal/render/wage/24048100.svg",
                    headers={"X-Internal-Share-Token": "share-secret"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("HEIGO WAGE CARD", response.text)
        self.assertIn("FINAL WAGE", response.text)

    def test_internal_render_roster_svg_returns_svg(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db, internal_share_token="share-secret"))
        client = TestClient(app)

        with patch("routers.frontend_routes.read_service.get_players_by_team", return_value=_sample_team_players()):
            with patch("routers.frontend_routes.read_service.get_team_info", return_value=_sample_team_info()):
                response = client.get(
                    "/internal/render/roster.svg?team=Barcelona&page=1",
                    headers={"X-Internal-Share-Token": "share-secret"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("HEIGO ROSTER", response.text)
        self.assertIn("Barcelona", response.text)
        self.assertIn("Players 6", response.text)
        self.assertIn("SLOT", response.text)
        self.assertIn("8M", response.text)
