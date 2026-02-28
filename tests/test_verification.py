from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.verification import build_verified_universe


class VerificationTest(unittest.TestCase):
    def test_build_verified_universe_filters_and_ranks(self) -> None:
        investors = [
            {
                "id": "a",
                "name_cn": "甲",
                "name_en": "A",
                "confidence": "C",
                "calibrated_return_pct": 30.0,
                "style": "测试",
            },
            {
                "id": "b",
                "name_cn": "乙",
                "name_en": "B",
                "confidence": "A",
                "calibrated_return_pct": 20.0,
                "style": "测试",
            },
            {
                "id": "c",
                "name_cn": "丙",
                "name_en": "C",
                "confidence": "B",
                "calibrated_return_pct": 25.0,
                "style": "测试",
            },
        ]

        result = build_verified_universe(investors, min_confidence="B")

        self.assertEqual(len(result.included), 2)
        self.assertEqual(len(result.excluded), 1)
        self.assertEqual(result.included[0]["id"], "c")
        self.assertEqual(result.included[0]["verified_rank"], 1)
        self.assertEqual(result.included[1]["id"], "b")
        self.assertEqual(result.excluded[0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
