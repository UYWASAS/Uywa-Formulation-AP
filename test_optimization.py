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

    def test_shadow_price_is_reported_for_binding_min_constraint(self):
        binding_df = pd.DataFrame(
            [
                {"Ingrediente": "Barato", "precio": 1.0, "EE": 0.0},
                {"Ingrediente": "Caro", "precio": 2.0, "EE": 20.0},
            ]
        )
        result = DietFormulator(
            binding_df,
            ["EE"],
            {"EE": {"min": 8.0, "max": 0}},
            self.limits,
        ).solve()

        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["shadow_prices"]["EE"], 0.05, places=4)

    def test_binding_shadow_price_relative_impact_uses_cost_per_kg_basis(self):
        binding_df = pd.DataFrame(
            [
                {"Ingrediente": "Barato", "precio": 1.0, "EE": 0.0},
                {"Ingrediente": "Caro", "precio": 2.0, "EE": 20.0},
            ]
        )
        result = DietFormulator(
            binding_df,
            ["EE"],
            {"EE": {"min": 8.0, "max": 0}},
            self.limits,
        ).solve()

        self.assertTrue(result["success"])
        total_cost_per_kg = result["cost"] / 100
        impact_pct = (abs(result["shadow_prices"]["EE"]) / total_cost_per_kg) * 100
        self.assertAlmostEqual(impact_pct, 3.5714, places=3)


if __name__ == "__main__":
    unittest.main()
