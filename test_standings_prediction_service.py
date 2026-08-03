import unittest

from services import standings_prediction_service


def _row(name: str, rank: int, *, played: int = 0, points: int = 0, goal_difference: int = 0):
    return {
        "level": "超级",
        "rank": rank,
        "team_name": name,
        "played": played,
        "points": points,
        "goal_difference": goal_difference,
        "goals_for": max(0, played + goal_difference),
        "wins": points // 3,
        "home_played": played // 2,
        "home_points": points // 2,
        "away_played": played - played // 2,
        "away_points": points - points // 2,
    }


class StandingsPredictionServiceTests(unittest.TestCase):
    def test_preseason_prediction_is_broad_and_waits_for_schedule(self):
        rows = [_row(f"Team {index}", index) for index in range(1, 7)]

        result = standings_prediction_service.predict_level("超级", rows, [], total_match_count=0)

        self.assertEqual(result["summary"]["phase_label"], "赛程待导入")
        self.assertEqual(result["summary"]["simulations"], 0)
        self.assertTrue(all(item["predicted_rank_min"] == 1 for item in result["teams"].values()))
        self.assertTrue(all(item["predicted_rank_max"] == 6 for item in result["teams"].values()))

    def test_real_remaining_fixtures_produce_deterministic_rank_ranges(self):
        rows = [
            _row("Alpha", 1, played=4, points=10, goal_difference=6),
            _row("Beta", 2, played=4, points=8, goal_difference=3),
            _row("Gamma", 3, played=4, points=5, goal_difference=0),
            _row("Delta", 4, played=4, points=4, goal_difference=-2),
        ]
        fixtures = [("Alpha", "Beta"), ("Gamma", "Delta"), ("Beta", "Gamma"), ("Delta", "Alpha")]

        first = standings_prediction_service.predict_level("超级", rows, fixtures, total_match_count=12)
        second = standings_prediction_service.predict_level("超级", rows, fixtures, total_match_count=12)

        self.assertEqual(first, second)
        self.assertEqual(first["summary"]["remaining_match_count"], 4)
        for item in first["teams"].values():
            self.assertLessEqual(item["predicted_rank_min"], item["predicted_rank"])
            self.assertLessEqual(item["predicted_rank"], item["predicted_rank_max"])
            self.assertGreaterEqual(item["prediction_confidence"], 0)
            self.assertLessEqual(item["prediction_confidence"], 1)

    def test_final_table_collapses_to_exact_rank(self):
        rows = [
            _row("Alpha", 1, played=10, points=24, goal_difference=12),
            _row("Beta", 2, played=10, points=18, goal_difference=5),
            _row("Gamma", 3, played=10, points=8, goal_difference=-8),
        ]

        result = standings_prediction_service.predict_level("超级", rows, [], total_match_count=15)

        self.assertEqual(result["summary"]["phase"], "final")
        for row in rows:
            item = result["teams"][row["team_name"]]
            self.assertEqual((item["predicted_rank_min"], item["predicted_rank"], item["predicted_rank_max"]), (row["rank"], row["rank"], row["rank"]))
            self.assertEqual(item["prediction_confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
