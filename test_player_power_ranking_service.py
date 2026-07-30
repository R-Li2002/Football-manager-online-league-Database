import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Player, Team
from services.player_power_ranking_service import (
    PowerCalibration,
    calculate_heigo_metrics,
    eligible_growth_steps,
    get_player_power_ranking,
    get_team_power_summaries,
)
from weighted_power import WEIGHTED_POWER_ACTIVE_WEIGHTS


def make_player(uid, *, ca=100, pa=190, value=10, pos_gk=1, name="测试球员"):
    payload = {
        "uid": uid,
        "name": name,
        "ca": ca,
        "pa": pa,
        "position": "MC",
        "club": "Test FC",
        "pos_gk": pos_gk,
        "left_foot": 10,
        "right_foot": 20,
    }
    for field, _weight in WEIGHTED_POWER_ACTIVE_WEIGHTS:
        payload[field] = value
    return SimpleNamespace(**payload)


class PlayerPowerRankingServiceTests(unittest.TestCase):
    def test_heigo_power_and_top_percent_share_the_same_relative_baseline(self):
        calibration = PowerCalibration(
            data_version="2630",
            player_count=5,
            median_score=65.0,
            mad=2.0,
            robust_scale=2.9652,
            sorted_scores=(55.0, 60.0, 65.0, 70.0, 75.0),
        )
        heigo_power, top_percent = calculate_heigo_metrics(70.0, calibration)
        self.assertEqual(heigo_power, 66.86)
        self.assertEqual(top_percent, 40.0)

    def test_growth_threshold_boundaries(self):
        expected = {
            10: [0], 11: [0, 1], 29: [0, 1], 30: [0, 1, 2],
            49: [0, 1, 2], 50: [0, 1, 2, 3], 69: [0, 1, 2, 3],
            70: [0, 1, 2, 3, 4], 89: [0, 1, 2, 3, 4],
            90: [0, 1, 2, 3, 4, 5],
        }
        for gap, steps in expected.items():
            with self.subTest(gap=gap):
                self.assertEqual([step for step, _gain in eligible_growth_steps(100, 100 + gap)], steps)

    @patch("services.player_power_ranking_service.map_player_uid_to_team_name", return_value={1: "测试队", 2: "测试队"})
    @patch("services.player_power_ranking_service.resolve_attribute_version", return_value="2630")
    @patch("services.player_power_ranking_service.iter_player_attributes")
    def test_allows_multiple_shapes_and_excludes_goalkeepers(self, iter_rows, _resolve, _team_map):
        iter_rows.return_value = [
            make_player(1, ca=100, pa=190, value=10),
            make_player(2, ca=100, pa=200, value=20, pos_gk=15, name="门将"),
        ]
        result = get_player_power_ranking(object(), shape="all", limit=20, data_version="2630")
        self.assertEqual(iter_rows.call_args.kwargs["player_uids"], {1, 2})
        self.assertEqual({item.growth_step for item in result.items}, {0, 1, 2, 3, 4, 5})
        self.assertEqual({item.uid for item in result.items}, {1})
        self.assertTrue(all(item.projected_ca <= item.pa for item in result.items))
        self.assertIn("+5", next(item.display_name for item in result.items if item.growth_step == 5))

    @patch("services.player_power_ranking_service.map_player_uid_to_team_name", return_value={1: "甲队", 2: "乙队"})
    @patch("services.player_power_ranking_service.resolve_attribute_version", return_value="2630")
    @patch("services.player_power_ranking_service.iter_player_attributes")
    def test_filters_team_and_shape_and_sorts_by_power(self, iter_rows, _resolve, _team_map):
        iter_rows.return_value = [make_player(1, value=8), make_player(2, value=15)]
        result = get_player_power_ranking(object(), shape="1", team_name="乙队", limit=10)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].uid, 2)
        self.assertEqual(result.items[0].growth_step, 1)
        self.assertEqual(result.items[0].ca_gain, 11)

    @patch("services.player_power_ranking_service.map_player_uid_to_team_name", return_value={1: "甲队", 2: "乙队"})
    @patch("services.player_power_ranking_service.resolve_attribute_version", return_value="2630")
    @patch("services.player_power_ranking_service.iter_player_attributes")
    def test_all_limit_returns_every_eligible_result_with_two_decimal_power(self, iter_rows, _resolve, _team_map):
        iter_rows.return_value = [make_player(1, ca=100, pa=111, value=9), make_player(2, ca=100, pa=100, value=12)]
        result = get_player_power_ranking(object(), shape="all", limit="all")
        self.assertEqual(result.limit, "all")
        self.assertEqual(len(result.items), 3)
        self.assertTrue(all(round(item.weighted_power, 2) == item.weighted_power for item in result.items))
        self.assertTrue(all(round(item.heigo_power, 2) == item.heigo_power for item in result.items))
        self.assertTrue(all(0 < item.top_percent <= 100 for item in result.items))

    @patch("services.player_power_ranking_service.resolve_attribute_version", return_value="2630")
    @patch("services.player_power_ranking_service.get_power_calibration")
    @patch("services.player_power_ranking_service.iter_player_attributes")
    def test_team_power_summaries_rank_roster_and_lineup_within_level(self, iter_rows, calibration, _resolve):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        try:
            teams = [
                Team(name="强队", manager="A", level="超级", wage=0, final_wage=0),
                Team(name="弱队", manager="B", level="超级", wage=0, final_wage=0),
            ]
            db.add_all(teams)
            db.flush()
            attributes = []
            for team_index, team in enumerate(teams):
                for offset in range(11):
                    uid = team_index * 100 + offset + 1
                    db.add(Player(uid=uid, name=f"P{uid}", team_id=team.id, team_name=team.name, position="M C", initial_ca=100, ca=100, pa=190, wage=0))
                    attributes.append(make_player(uid, value=18 if team_index == 0 else 8))
            db.commit()
            iter_rows.return_value = attributes
            calibration.return_value = PowerCalibration("2630", 22, 50.0, 1.0, 10.0, tuple(range(22)))

            result = get_team_power_summaries(db)
            by_name = {item.team_name: item for item in result.items}
            self.assertEqual(by_name["强队"].roster_rank, 1)
            self.assertEqual(by_name["强队"].lineup_rank, 1)
            self.assertEqual(by_name["弱队"].roster_rank, 2)
            self.assertEqual(by_name["强队"].lineup_player_count, 11)
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
