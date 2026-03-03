from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.top20_pack import build_group_profiles
from investor_method_lab.top20_pack_v4 import build_v4_analysis, prepare_rows_with_market_norm


class Top20PackV4Test(unittest.TestCase):
    def _profiles(self):
        investors = [
            {
                "id": "buffett",
                "name_cn": "巴菲特",
                "methodology_bucket": "价值质量复利",
            }
        ]
        framework = {
            "groups": [
                {
                    "id": "value_quality_compound",
                    "name": "价值质量复利",
                    "base_strategy_id": "value_quality",
                    "core_question": "测试",
                    "bucket_matches": ["价值质量复利"],
                }
            ]
        }
        strategies = [
            {
                "id": "value_quality",
                "weights": {
                    "margin_of_safety": 0.3,
                    "quality": 0.25,
                    "growth": 0.1,
                    "momentum": 0.1,
                    "catalyst": 0.1,
                    "risk_control": 0.15,
                },
            }
        ]
        return build_group_profiles(investors, framework, strategies)

    def _rulebook(self):
        return {
            "version": "v4-test",
            "defaults": {
                "near_miss_tolerance": 0.03,
                "tiering": {
                    "core_min_score": 60.0,
                    "tactical_min_score": 40.0,
                    "watch_multiplier": 0.8,
                },
            },
            "tier_weights": {
                "core": 1.0,
                "watch": 0.78,
                "tactical": 0.9,
                "rejected": 0.0,
            },
            "groups": [
                {
                    "id": "value_quality_compound",
                    "name": "价值质量复利",
                    "default": {
                        "hard_rules": [
                            {
                                "field": "margin_of_safety_raw",
                                "op": ">=",
                                "value": 0.1,
                                "label": "MOS>=10%",
                            },
                            {
                                "field": "quality_score_raw",
                                "op": ">=",
                                "value": 60.0,
                                "label": "质量>=60",
                            },
                        ],
                        "soft_rules": [
                            {
                                "field": "certainty_score_raw",
                                "op": "<",
                                "value": 50.0,
                                "multiplier": 0.8,
                                "label": "确定性<50",
                            }
                        ],
                        "tiering": {
                            "core_min_score": 60.0,
                            "tactical_min_score": 40.0,
                            "watch_multiplier": 0.8,
                        },
                    },
                    "market_overrides": {
                        "A": {
                            "hard_rules": [
                                {
                                    "field": "margin_of_safety_raw",
                                    "op": ">=",
                                    "value": 0.1,
                                    "label": "A MOS>=10%",
                                },
                                {
                                    "field": "quality_score_raw",
                                    "op": ">=",
                                    "value": 60.0,
                                    "label": "A 质量>=60",
                                },
                            ]
                        },
                        "HK": {},
                        "US": {
                            "hard_rules": [
                                {
                                    "field": "margin_of_safety_raw",
                                    "op": ">=",
                                    "value": 0.1,
                                    "label": "US MOS>=10%",
                                },
                                {
                                    "field": "quality_score_raw",
                                    "op": ">=",
                                    "value": 60.0,
                                    "label": "US 质量>=60",
                                },
                            ]
                        },
                    },
                }
            ],
        }

    def test_hard_fail_has_explicit_reason(self) -> None:
        profiles = self._profiles()
        opportunities = [
            {
                "ticker": "AAA",
                "name": "AAA",
                "sector": "Tech",
                "price_to_fair_value": "1.30",
                "quality_score": "80",
                "growth_score": "50",
                "momentum_score": "55",
                "catalyst_score": "50",
                "risk_score": "30",
                "certainty_score": "70",
            }
        ]
        result = build_v4_analysis(opportunities, profiles, self._rulebook(), top_n=10)
        trace = result["decision_trace_rows"][0]["groups"][0]
        self.assertFalse(trace["hard_pass"])
        self.assertEqual(trace["tier"], "rejected")
        self.assertIn("MOS", " ".join(trace["hard_fail_reasons"]))

    def test_near_miss_goes_to_watch(self) -> None:
        profiles = self._profiles()
        opportunities = [
            {
                "ticker": "BBB",
                "name": "BBB",
                "sector": "Tech",
                "price_to_fair_value": "0.92",
                "quality_score": "80",
                "growth_score": "55",
                "momentum_score": "55",
                "catalyst_score": "55",
                "risk_score": "30",
                "certainty_score": "70",
            }
        ]
        result = build_v4_analysis(opportunities, profiles, self._rulebook(), top_n=10)
        trace = result["decision_trace_rows"][0]["groups"][0]
        self.assertFalse(trace["hard_pass"])
        self.assertTrue(trace["near_miss"])
        self.assertEqual(trace["tier"], "watch")

    def test_soft_penalty_updates_multiplier_and_score(self) -> None:
        profiles = self._profiles()
        opportunities = [
            {
                "ticker": "CCC",
                "name": "CCC",
                "sector": "Tech",
                "price_to_fair_value": "0.80",
                "quality_score": "85",
                "growth_score": "70",
                "momentum_score": "65",
                "catalyst_score": "60",
                "risk_score": "20",
                "certainty_score": "20",
            }
        ]
        result = build_v4_analysis(opportunities, profiles, self._rulebook(), top_n=10)
        trace = result["decision_trace_rows"][0]["groups"][0]
        self.assertTrue(trace["hard_pass"])
        self.assertEqual(trace["penalty_multiplier"], 0.8)
        self.assertLess(trace["adjusted_score"], trace["base_score"])
        self.assertIn("确定性<50", " ".join(item["rule"] for item in trace["soft_penalties"]))

    def test_market_normalization_stays_inside_market(self) -> None:
        opportunities = [
            {
                "ticker": "600000.SS",
                "name": "A_HIGH",
                "sector": "Finance",
                "price_to_fair_value": "0.8",
                "quality_score": "90",
                "growth_score": "60",
                "momentum_score": "50",
                "catalyst_score": "50",
                "risk_score": "20",
            },
            {
                "ticker": "000001.SZ",
                "name": "A_LOW",
                "sector": "Finance",
                "price_to_fair_value": "0.8",
                "quality_score": "70",
                "growth_score": "60",
                "momentum_score": "50",
                "catalyst_score": "50",
                "risk_score": "20",
            },
            {
                "ticker": "MSFT",
                "name": "US_HIGH",
                "sector": "Tech",
                "price_to_fair_value": "0.8",
                "quality_score": "60",
                "growth_score": "60",
                "momentum_score": "50",
                "catalyst_score": "50",
                "risk_score": "20",
            },
            {
                "ticker": "AAPL",
                "name": "US_LOW",
                "sector": "Tech",
                "price_to_fair_value": "0.8",
                "quality_score": "40",
                "growth_score": "60",
                "momentum_score": "50",
                "catalyst_score": "50",
                "risk_score": "20",
            },
        ]
        rows = prepare_rows_with_market_norm(opportunities)
        by_ticker = {row["ticker"]: row for row in rows}
        self.assertGreater(
            by_ticker["600000.SS"]["market_norm_quality"],
            by_ticker["000001.SZ"]["market_norm_quality"],
        )
        self.assertGreater(
            by_ticker["MSFT"]["market_norm_quality"],
            by_ticker["AAPL"]["market_norm_quality"],
        )

    def test_build_v4_analysis_output_shape(self) -> None:
        profiles = self._profiles()
        opportunities = [
            {
                "ticker": "DDD",
                "name": "DDD",
                "sector": "Tech",
                "price_to_fair_value": "0.78",
                "quality_score": "82",
                "growth_score": "68",
                "momentum_score": "63",
                "catalyst_score": "59",
                "risk_score": "22",
                "certainty_score": "65",
            }
        ]
        result = build_v4_analysis(
            opportunities,
            profiles,
            self._rulebook(),
            top_n=10,
            per_group_top_n=5,
            per_tier_top_n=10,
        )
        self.assertIn("top_rows", result)
        self.assertIn("tiered_group_rows", result)
        self.assertIn("decision_trace_rows", result)
        self.assertEqual(len(result["decision_trace_rows"]), 1)
        top_row = result["top_rows"][0]
        self.assertIn("explain_group_trace_json", top_row)
        self.assertIn("explain_market", top_row)


if __name__ == "__main__":
    unittest.main()
