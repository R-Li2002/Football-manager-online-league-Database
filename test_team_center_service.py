import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import read_service, team_center_service


class TeamCenterServiceTests(unittest.TestCase):
    def test_read_service_forwards_prediction_toggle(self):
        db = object()
        expected = object()
        with patch("services.read_service.match_service.get_standings", return_value=expected) as get_standings:
            result = read_service.get_standings(db, level="甲级", include_predictions=False)

        self.assertIs(result, expected)
        get_standings.assert_called_once_with(db, level="甲级", include_predictions=False)

    def test_team_center_only_loads_current_level_without_predictions(self):
        db = MagicMock()
        team = SimpleNamespace(id=7, name="测试队", level="乙级")
        db.query.return_value.filter.return_value.first.return_value = team

        class StopAfterStandings(Exception):
            pass

        with (
            patch("services.team_center_service.read_service.get_teams", return_value=[SimpleNamespace(id=7)]),
            patch(
                "services.team_center_service.read_service.get_standings",
                side_effect=StopAfterStandings,
            ) as get_standings,
        ):
            with self.assertRaises(StopAfterStandings):
                team_center_service.get_team_center(db, team.id)

        get_standings.assert_called_once_with(
            db,
            level="乙级",
            include_predictions=False,
        )


if __name__ == "__main__":
    unittest.main()
