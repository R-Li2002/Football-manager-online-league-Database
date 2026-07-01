import unittest

from wage_calculator import calculate_wage


class WageCalculatorTest(unittest.TestCase):
    def test_goalkeeper_position_is_normalized_for_slot_coefficient(self):
        result = calculate_wage(
            initial_ca=150,
            current_ca=150,
            pa=170,
            age=20,
            position="GK ",
            growth_age_limit=23,
        )

        self.assertEqual(result["slot_type"], "伪名")
        self.assertEqual(result["coefficient"], 0.1)
        self.assertEqual(result["wage"], 0.6)

    def test_one_million_value_uses_floor_coefficient(self):
        result = calculate_wage(
            initial_ca=68,
            current_ca=68,
            pa=130,
            age=16,
            position="AM/S L",
            growth_age_limit=23,
        )

        self.assertEqual(result["final_value"], 1)
        self.assertEqual(result["coefficient"], 0.1)
        self.assertEqual(result["wage"], 0.1)

    def test_non_growth_pa_uses_current_value(self):
        result = calculate_wage(
            initial_ca=130,
            current_ca=150,
            pa=139,
            age=20,
            position="MC",
            growth_age_limit=23,
        )

        self.assertEqual(result["initial_value"], 3)
        self.assertEqual(result["current_value"], 5)
        self.assertEqual(result["final_value"], 5)
        self.assertEqual(result["wage"], 0.35)


if __name__ == "__main__":
    unittest.main()
