from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.scoring import compute_factors, rank_opportunities


class ScoringTest(unittest.TestCase):
    def test_compute_factors_caps_values(self) -> None:
        row = {
            "price_to_fair_value": "0.8",
            "quality_score": "120",
            "growth_score": "-20",
            "momentum_score": "65",
            "catalyst_score": "70",
            "risk_score": "10",
        }
        factors = compute_factors(row)

        self.assertAlmostEqual(factors["margin_of_safety"], 0.2)
        self.assertAlmostEqual(factors["quality"], 1.0)
        self.assertAlmostEqual(factors["growth"], 0.0)
        self.assertAlmostEqual(factors["risk_control"], 0.9)

    def test_rank_opportunities_orders_by_score(self) -> None:
        strategy = {
            "weights": {
                "margin_of_safety": 0.5,
                "quality": 0.2,
                "growth": 0.1,
                "momentum": 0.1,
                "catalyst": 0.05,
                "risk_control": 0.05,
            }
        }
        opportunities = [
            {
                "ticker": "AAA",
                "name": "Alpha",
                "price_to_fair_value": "0.6",
                "quality_score": "80",
                "growth_score": "50",
                "momentum_score": "40",
                "catalyst_score": "45",
                "risk_score": "25",
            },
            {
                "ticker": "BBB",
                "name": "Beta",
                "price_to_fair_value": "1.1",
                "quality_score": "90",
                "growth_score": "90",
                "momentum_score": "90",
                "catalyst_score": "90",
                "risk_score": "10",
            },
        ]

        ranked = rank_opportunities(opportunities, strategy, top_n=2)
        self.assertEqual(ranked[0]["ticker"], "AAA")


if __name__ == "__main__":
    unittest.main()
