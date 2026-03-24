from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from models import PlayerAttributeVersion
from routers.public_routes import build_public_router
from services.read_service import get_player_reaction_leaderboard


def _make_row(
    *,
    uid: int,
    name: str,
    heigo_club: str,
    flowers: int,
    eggs: int,
    net_score: int,
    total_reactions: int,
):
    return SimpleNamespace(
        uid=uid,
        name=name,
        position="MC",
        age=22,
        ca=140,
        pa=160,
        heigo_club=heigo_club,
        flowers=flowers,
        eggs=eggs,
        net_score=net_score,
        total_reactions=total_reactions,
        updated_at=None,
    )


class ReactionLeaderboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = object()

    @patch("services.read_service.list_player_reaction_leaderboard_rows")
    @patch("services.read_service.list_available_attribute_versions")
    @patch("services.read_service.resolve_attribute_version")
    def test_service_returns_ranked_items(self, mock_resolve_version, mock_list_versions, mock_list_rows):
        mock_resolve_version.return_value = "2620"
        mock_list_versions.return_value = ["2620"]
        mock_list_rows.return_value = [
            _make_row(uid=7, name="Alpha", heigo_club="Alpha FC", flowers=12, eggs=2, net_score=10, total_reactions=14),
            _make_row(uid=8, name="Beta", heigo_club="Beta FC", flowers=10, eggs=1, net_score=9, total_reactions=11),
        ]

        response = get_player_reaction_leaderboard(
            self.db,
            metric="flowers",
            limit=20,
            team_name="Alpha FC",
            data_version="2620",
        )

        self.assertEqual(response.metric, "flowers")
        self.assertEqual(response.limit, 20)
        self.assertEqual(response.team, "Alpha FC")
        self.assertEqual(response.data_version, "2620")
        self.assertEqual(len(response.items), 2)
        self.assertEqual(response.items[0].uid, 7)
        self.assertEqual(response.items[0].heigo_club, "Alpha FC")

        _, kwargs = mock_list_rows.call_args
        self.assertIs(kwargs["attribute_model"], PlayerAttributeVersion)
        self.assertEqual(kwargs["data_version"], "2620")
        self.assertEqual(kwargs["metric"], "flowers")
        self.assertEqual(kwargs["team_name"], "Alpha FC")
        self.assertEqual(kwargs["limit"], 20)

    @patch("services.read_service.list_player_reaction_leaderboard_rows")
    @patch("services.read_service.list_available_attribute_versions")
    @patch("services.read_service.resolve_attribute_version")
    def test_service_clamps_limit_into_supported_range(self, mock_resolve_version, mock_list_versions, mock_list_rows):
        mock_resolve_version.return_value = "2620"
        mock_list_versions.return_value = ["2620"]
        mock_list_rows.return_value = []

        get_player_reaction_leaderboard(self.db, metric="eggs", limit=0)
        _, kwargs_min = mock_list_rows.call_args
        self.assertEqual(kwargs_min["limit"], 1)

        get_player_reaction_leaderboard(self.db, metric="net", limit=500)
        _, kwargs_max = mock_list_rows.call_args
        self.assertEqual(kwargs_max["limit"], 100)

    def test_service_rejects_invalid_metric(self):
        with self.assertRaisesRegex(Exception, "flowers"):
            get_player_reaction_leaderboard(self.db, metric="invalid", limit=20)


class ReactionLeaderboardRouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()

        def get_db():
            yield object()

        app.include_router(build_public_router(get_db))
        self.client = TestClient(app)

    @patch("services.read_service.list_player_reaction_leaderboard_rows")
    @patch("services.read_service.list_available_attribute_versions")
    @patch("services.read_service.resolve_attribute_version")
    def test_route_returns_leaderboard_payload(self, mock_resolve_version, mock_list_versions, mock_list_rows):
        mock_resolve_version.return_value = "2620"
        mock_list_versions.return_value = ["2620"]
        mock_list_rows.return_value = [
            _make_row(uid=9, name="Gamma", heigo_club="Gamma FC", flowers=8, eggs=3, net_score=5, total_reactions=11),
        ]

        response = self.client.get(
            "/api/reactions/leaderboard",
            params={"metric": "net", "limit": 5, "team": "Gamma FC", "version": "2620"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["metric"], "net")
        self.assertEqual(payload["limit"], 5)
        self.assertEqual(payload["team"], "Gamma FC")
        self.assertEqual(payload["data_version"], "2620")
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["name"], "Gamma")
        self.assertEqual(payload["items"][0]["net_score"], 5)

    def test_route_rejects_invalid_metric(self):
        response = self.client.get("/api/reactions/leaderboard", params={"metric": "unknown"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("flowers", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
