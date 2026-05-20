import unittest

import pandas as pd

from optimization import DietFormulator


class DietFormulatorMaxConstraintTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            [
                {"Ingrediente": "A", "precio": 1.0, "EE": 20.0},
                {"Ingrediente": "B", "precio": 2.0, "EE": 0.0},
            ]
        )
        self.limits = {"min": {}, "max": {}}

    def test_positive_nutritional_max_is_enforced(self):
        result = DietFormulator(
            self.df,
            ["EE"],
            {"EE": {"min": 0, "max": 8.0}},
            self.limits,
        ).solve()

        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["nutritional_values"]["EE"], 8.0)
        self.assertLessEqual(result["nutritional_values"]["EE"], 8.0)

    def test_empty_zero_or_none_max_means_no_maximum(self):
        for raw_max in (None, "", 0):
            with self.subTest(raw_max=raw_max):
                result = DietFormulator(
                    self.df,
                    ["EE"],
                    {"EE": {"min": 0, "max": raw_max}},
                    self.limits,
                ).solve()

                self.assertTrue(result["success"])
                self.assertAlmostEqual(result["nutritional_values"]["EE"], 20.0)

    def test_infeasible_positive_max_returns_solver_status(self):
        infeasible_df = pd.DataFrame(
            [{"Ingrediente": "Solo", "precio": 1.0, "EE": 20.0}]
        )
        result = DietFormulator(
            infeasible_df,
            ["EE"],
            {"EE": {"min": 0, "max": 8.0}},
            self.limits,
        ).solve()

        self.assertFalse(result["success"])
        self.assertIn("Infeasible", result["message"])


if __name__ == "__main__":
    unittest.main()
