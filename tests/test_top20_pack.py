from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.top20_pack import (
    build_group_profiles,
    rank_diversified_opportunities,
    rank_opportunities_for_each_group,
    rank_first_batch_opportunities,
    render_opportunity_pack_markdown,
)


class Top20PackTest(unittest.TestCase):
    def _sample_profiles(self):
        investors = [
            {
                "id": "warren_buffett",
                "name_cn": "沃伦·巴菲特",
                "methodology_bucket": "价值质量复利",
            },
            {
                "id": "peter_lynch",
                "name_cn": "彼得·林奇",
                "methodology_bucket": "GARP 成长",
            },
        ]
        framework = {
            "groups": [
                {
                    "id": "value_quality_compound",
                    "name": "价值",
                    "base_strategy_id": "value_quality",
                    "core_question": "测试",
                    "bucket_matches": ["价值质量复利"],
                },
                {
                    "id": "garp_growth",
                    "name": "成长",
                    "base_strategy_id": "growth_at_reasonable_price",
                    "core_question": "测试",
                    "bucket_matches": ["GARP 成长"],
                },
            ]
        }
        strategies = [
            {
                "id": "value_quality",
                "weights": {
                    "margin_of_safety": 0.3,
                    "quality": 0.3,
                    "growth": 0.1,
                    "momentum": 0.1,
                    "catalyst": 0.1,
                    "risk_control": 0.1,
                },
            },
            {
                "id": "growth_at_reasonable_price",
                "weights": {
                    "margin_of_safety": 0.1,
                    "quality": 0.2,
                    "growth": 0.3,
                    "momentum": 0.1,
                    "catalyst": 0.2,
                    "risk_control": 0.1,
                },
            },
        ]
        return build_group_profiles(investors, framework, strategies)

    def test_group_profiles_and_ranking(self) -> None:
        profiles = self._sample_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertAlmostEqual(sum(p.group_weight for p in profiles), 1.0)

        opportunities = [
            {
                "ticker": "AAA",
                "name": "A",
                "sector": "Tech",
                "price_to_fair_value": "0.8",
                "quality_score": "85",
                "growth_score": "70",
                "momentum_score": "60",
                "catalyst_score": "65",
                "risk_score": "20",
                "note": "good",
            },
            {
                "ticker": "BBB",
                "name": "B",
                "sector": "Tech",
                "price_to_fair_value": "1.2",
                "quality_score": "90",
                "growth_score": "90",
                "momentum_score": "90",
                "catalyst_score": "90",
                "risk_score": "10",
                "note": "high growth",
            },
        ]
        ranked = rank_first_batch_opportunities(opportunities, profiles, top_n=2)
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(ranked[0]["composite_score"], ranked[1]["composite_score"])

    def test_render_markdown_escapes_table_cells(self) -> None:
        profiles = build_group_profiles(
            investors=[
                {
                    "id": "warren_buffett",
                    "name_cn": "沃伦·巴菲特",
                    "methodology_bucket": "价值质量复利",
                }
            ],
            framework={
                "groups": [
                    {
                        "id": "value",
                        "name": "价值|复利",
                        "base_strategy_id": "value_quality",
                        "core_question": "测试|问题",
                        "bucket_matches": ["价值质量复利"],
                    }
                ]
            },
            strategies=[
                {
                    "id": "value_quality",
                    "weights": {
                        "margin_of_safety": 0.3,
                        "quality": 0.3,
                        "growth": 0.1,
                        "momentum": 0.1,
                        "catalyst": 0.1,
                        "risk_control": 0.1,
                    },
                }
            ],
        )

        markdown = render_opportunity_pack_markdown(
            as_of_date="2026-02-27",
            profiles=profiles,
            top_rows=[
                {
                    "ticker": "AAA",
                    "name": "A",
                    "sector": "Tech",
                    "composite_score": 60.0,
                    "best_group": "价值|复利",
                    "best_reason": "催化:19.5 | 趋势:15.1",
                    "note": "note|1",
                }
            ],
        )
        self.assertIn("价值\\|复利", markdown)
        self.assertIn("催化:19.5 \\| 趋势:15.1", markdown)
        self.assertIn("note\\|1", markdown)
        self.assertIn("## 6) 安全边际口径参照", markdown)
        self.assertIn("MOS_FV = (FV - P) / FV", markdown)
        self.assertIn("docs/margin_of_safety_references.md", markdown)

    def test_rank_opportunities_for_each_group(self) -> None:
        profiles = self._sample_profiles()
        opportunities = [
            {
                "ticker": "A1",
                "name": "A1",
                "sector": "Tech",
                "price_to_fair_value": "0.7",
                "quality_score": "80",
                "growth_score": "60",
                "momentum_score": "50",
                "catalyst_score": "50",
                "risk_score": "20",
                "note": "value-ish",
            },
            {
                "ticker": "G1",
                "name": "G1",
                "sector": "Tech",
                "price_to_fair_value": "1.0",
                "quality_score": "85",
                "growth_score": "95",
                "momentum_score": "70",
                "catalyst_score": "80",
                "risk_score": "25",
                "note": "growth",
            },
            {
                "ticker": "A2",
                "name": "A2",
                "sector": "Finance",
                "price_to_fair_value": "0.75",
                "quality_score": "90",
                "growth_score": "55",
                "momentum_score": "45",
                "catalyst_score": "40",
                "risk_score": "18",
                "note": "value",
            },
        ]

        rows_by_group = rank_opportunities_for_each_group(
            opportunities, profiles, top_n_per_group=2
        )
        self.assertEqual(len(rows_by_group), 2)
        for _, rows in rows_by_group:
            self.assertEqual(len(rows), 2)
            self.assertGreaterEqual(rows[0]["group_score"], rows[1]["group_score"])

    def test_rank_diversified_opportunities_sector_limit(self) -> None:
        profiles = self._sample_profiles()
        opportunities = [
            {
                "ticker": "T1",
                "name": "T1",
                "sector": "Technology",
                "price_to_fair_value": "0.7",
                "quality_score": "90",
                "growth_score": "80",
                "momentum_score": "70",
                "catalyst_score": "70",
                "risk_score": "20",
                "note": "",
            },
            {
                "ticker": "T2",
                "name": "T2",
                "sector": "Technology",
                "price_to_fair_value": "0.72",
                "quality_score": "88",
                "growth_score": "78",
                "momentum_score": "68",
                "catalyst_score": "68",
                "risk_score": "22",
                "note": "",
            },
            {
                "ticker": "T3",
                "name": "T3",
                "sector": "Technology",
                "price_to_fair_value": "0.74",
                "quality_score": "86",
                "growth_score": "76",
                "momentum_score": "66",
                "catalyst_score": "66",
                "risk_score": "24",
                "note": "",
            },
            {
                "ticker": "F1",
                "name": "F1",
                "sector": "Financial",
                "price_to_fair_value": "0.76",
                "quality_score": "84",
                "growth_score": "74",
                "momentum_score": "64",
                "catalyst_score": "64",
                "risk_score": "26",
                "note": "",
            },
            {
                "ticker": "H1",
                "name": "H1",
                "sector": "Healthcare",
                "price_to_fair_value": "0.78",
                "quality_score": "82",
                "growth_score": "72",
                "momentum_score": "62",
                "catalyst_score": "62",
                "risk_score": "28",
                "note": "",
            },
        ]

        diversified = rank_diversified_opportunities(
            opportunities,
            profiles,
            top_n=3,
            max_per_sector=1,
        )
        self.assertEqual(len(diversified), 3)
        sectors = [row["sector"] for row in diversified]
        self.assertLessEqual(sectors.count("Technology"), 1)

    def test_value_quality_guardrails_filter_low_margin_and_low_certainty(self) -> None:
        profiles = self._sample_profiles()
        value_profile = [p for p in profiles if p.id == "value_quality_compound"][0]

        opportunities = [
            {
                "ticker": "PASS",
                "name": "PASS",
                "sector": "Tech",
                "price_to_fair_value": "0.75",
                "quality_score": "90",
                "growth_score": "70",
                "momentum_score": "60",
                "catalyst_score": "65",
                "risk_score": "20",
                "certainty_score": "80",
                "note": "",
            },
            {
                "ticker": "LOW_MARGIN",
                "name": "LOW_MARGIN",
                "sector": "Tech",
                "price_to_fair_value": "0.95",
                "quality_score": "95",
                "growth_score": "80",
                "momentum_score": "70",
                "catalyst_score": "80",
                "risk_score": "15",
                "certainty_score": "90",
                "note": "",
            },
            {
                "ticker": "LOW_CERTAINTY",
                "name": "LOW_CERTAINTY",
                "sector": "Tech",
                "price_to_fair_value": "0.70",
                "quality_score": "90",
                "growth_score": "70",
                "momentum_score": "60",
                "catalyst_score": "65",
                "risk_score": "20",
                "certainty_score": "60",
                "note": "",
            },
        ]

        grouped = rank_opportunities_for_each_group(opportunities, profiles, top_n_per_group=5)
        for profile, rows in grouped:
            if profile.id != value_profile.id:
                continue
            tickers = [row["ticker"] for row in rows]
            self.assertEqual(tickers, ["PASS"])

    def test_trend_following_guardrails_filter_low_momentum(self) -> None:
        profiles = build_group_profiles(
            investors=[
                {
                    "id": "trend_investor",
                    "name_cn": "趋势交易员",
                    "methodology_bucket": "趋势交易",
                }
            ],
            framework={
                "groups": [
                    {
                        "id": "trend_following",
                        "name": "趋势跟随",
                        "base_strategy_id": "trend_following",
                        "core_question": "测试",
                        "bucket_matches": ["趋势交易"],
                    }
                ]
            },
            strategies=[
                {
                    "id": "trend_following",
                    "weights": {
                        "margin_of_safety": 0.05,
                        "quality": 0.08,
                        "growth": 0.13,
                        "momentum": 0.41,
                        "catalyst": 0.23,
                        "risk_control": 0.10,
                    },
                }
            ],
        )
        opportunities = [
            {
                "ticker": "PASS_TREND",
                "name": "PASS_TREND",
                "sector": "Tech",
                "price_to_fair_value": "1.05",
                "quality_score": "55",
                "growth_score": "70",
                "momentum_score": "82",
                "catalyst_score": "72",
                "risk_score": "35",
                "note": "",
            },
            {
                "ticker": "LOW_MOMENTUM",
                "name": "LOW_MOMENTUM",
                "sector": "Tech",
                "price_to_fair_value": "0.95",
                "quality_score": "70",
                "growth_score": "75",
                "momentum_score": "58",
                "catalyst_score": "70",
                "risk_score": "30",
                "note": "",
            },
        ]
        grouped = rank_opportunities_for_each_group(opportunities, profiles, top_n_per_group=5)
        self.assertEqual(len(grouped), 1)
        _, rows = grouped[0]
        tickers = [row["ticker"] for row in rows]
        self.assertEqual(tickers, ["PASS_TREND"])


if __name__ == "__main__":
    unittest.main()
