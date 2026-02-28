from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.investor_ranking import rank_investors


class InvestorRankingTest(unittest.TestCase):
    def test_rank_investors(self) -> None:
        investors = [
            {
                "id": "a",
                "name": "A",
                "metrics": {
                    "performance": 90,
                    "risk_control": 90,
                    "longevity": 90,
                    "transparency": 90,
                },
            },
            {
                "id": "b",
                "name": "B",
                "metrics": {
                    "performance": 80,
                    "risk_control": 80,
                    "longevity": 80,
                    "transparency": 80,
                },
            },
        ]
        weights = {
            "performance": 0.4,
            "risk_control": 0.2,
            "longevity": 0.2,
            "transparency": 0.2,
        }

        ranked = rank_investors(investors, weights, top_n=2)
        self.assertEqual(ranked[0]["id"], "a")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])


if __name__ == "__main__":
    unittest.main()
