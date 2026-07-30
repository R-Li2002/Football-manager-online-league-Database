import unittest

from weighted_power import WEIGHTED_POWER_ACTIVE_WEIGHTS, calculate_weighted_power


class WeightedPowerTests(unittest.TestCase):
    @staticmethod
    def _boundary_player(positive_value: float, negative_value: float) -> dict:
        player = {"pos_gk": 1}
        for field, weight in WEIGHTED_POWER_ACTIVE_WEIGHTS:
            player[field] = negative_value if weight < 0 else positive_value
        return player

    def test_normalizes_theoretical_boundaries_and_midpoint(self):
        self.assertEqual(calculate_weighted_power(self._boundary_player(1, 20)).score, 0)
        self.assertEqual(calculate_weighted_power(self._boundary_player(20, 1)).score, 100)
        self.assertEqual(calculate_weighted_power(self._boundary_player(10.5, 10.5)).score, 50)

    def test_ignores_missing_attributes(self):
        result = calculate_weighted_power({"pos_gk": 1, "passing": 10.5})
        self.assertEqual(result.score, 50)
        self.assertEqual(result.included, 1)

    def test_supports_two_decimal_precision_for_rankings(self):
        player = {"pos_gk": 1, "passing": 7}
        self.assertEqual(calculate_weighted_power(player).score, 31.58)
        self.assertEqual(calculate_weighted_power(player, precision=1).score, 31.6)
        self.assertEqual(calculate_weighted_power(player, precision=2).score, 31.58)

    def test_goalkeeper_is_not_scored(self):
        result = calculate_weighted_power({"pos_gk": 15, "passing": 20})
        self.assertIsNone(result.score)
        self.assertTrue(result.is_goalkeeper)


if __name__ == "__main__":
    unittest.main()
