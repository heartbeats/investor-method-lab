from __future__ import annotations

import unittest

import investor_method_lab.valuation_upgrade_backlog as backlog_module
from investor_method_lab.valuation_upgrade_backlog import (
    build_source_upgrade_backlog,
    classify_gap_item,
    infer_market,
)


class ValuationUpgradeBacklogTests(unittest.TestCase):
    def test_infer_market(self) -> None:
        self.assertEqual(infer_market("600519.SS"), "A")
        self.assertEqual(infer_market("0700.HK"), "HK")
        self.assertEqual(infer_market("MSFT"), "US")

    def test_classify_reference_only_a_share_as_dcf_focus_expansion(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "600919.SS",
                "name": "江苏银行",
                "method_group": "宏观周期",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "A", "signal_id": "s1", "as_of_date": "2026-03-05"},
            dcf_gap_batch_meta={"batch_kind": "dcf_focus_expansion"},
        )
        self.assertEqual(item["upgrade_lane"], "dcf_focus_expansion")
        self.assertEqual(item["target_support_tier"], "formal_core")
        self.assertEqual(item["priority"], "P1")

    def test_classify_reference_only_a_share_as_structural_dcf_base_batch(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "688126.SS",
                "name": "沪硅产业",
                "method_group": "宏观周期",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "A", "signal_id": "s3", "as_of_date": "2026-03-12"},
            dcf_gap_batch_meta={"batch_kind": "structural_dcf_base", "reason": "no financial shell model and valuation_mode=parameterized_only"},
        )
        self.assertEqual(item["upgrade_lane"], "structural_dcf_base_batch")
        self.assertEqual(item["issue_type"], "structural_dcf_base_blocked")
        self.assertEqual(item["target_support_tier"], "formal_core")
        self.assertEqual(item["priority"], "P1")

    def test_classify_reference_only_a_share_as_non_positive_dcf_hold(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "688126.SS",
                "name": "沪硅产业",
                "method_group": "宏观周期",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_missing_payload)"},
            signal_row={"market": "A", "signal_id": "s4", "as_of_date": "2026-03-13"},
            dcf_gap_batch_meta={"batch_kind": "non_positive_dcf_hold", "reason": "latest valuation exists but iv_base<=0 (-41.8946)"},
        )
        self.assertEqual(item["upgrade_lane"], "formalization_review")
        self.assertEqual(item["issue_type"], "dcf_non_positive_iv")
        self.assertEqual(item["target_support_tier"], "reference_only")
        self.assertEqual(item["priority"], "P2")


    def test_classify_reference_only_a_share_as_reference_only_template_hold(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "600515.SS",
                "name": "海南机场",
                "method_group": "宏观周期",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "A", "signal_id": "s6", "as_of_date": "2026-03-13"},
            dcf_gap_batch_meta={"batch_kind": "reference_only_template_hold", "reason": "template is reference_only / non-DCF-friendly"},
        )
        self.assertEqual(item["upgrade_lane"], "formalization_review")
        self.assertEqual(item["issue_type"], "reference_only_template_hold")
        self.assertEqual(item["target_support_tier"], "reference_only")
        self.assertEqual(item["priority"], "P2")

    def test_classify_reference_only_a_share_as_snapshot_seed_batch(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "688506.SS",
                "name": "百利天恒",
                "method_group": "宏观周期",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "A", "signal_id": "s5", "as_of_date": "2026-03-13"},
            dcf_gap_batch_meta={"batch_kind": "snapshot_seed_batch", "reason": "company seed exists but approved financial snapshot is still missing"},
        )
        self.assertEqual(item["upgrade_lane"], "snapshot_seed_batch")
        self.assertEqual(item["issue_type"], "snapshot_seed_blocked")
        self.assertEqual(item["target_support_tier"], "formal_core")
        self.assertEqual(item["priority"], "P1")


    def test_classify_reference_only_us_as_reference_only_template_hold(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "BXP",
                "name": "BXP, Inc.",
                "method_group": "系统化量化",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "US", "signal_id": "s7", "as_of_date": "2026-03-14"},
            dcf_gap_batch_meta={"batch_kind": "reference_only_template_hold", "reason": "template is reference_only / non-DCF-friendly"},
        )
        self.assertEqual(item["upgrade_lane"], "formalization_review")
        self.assertEqual(item["issue_type"], "reference_only_template_hold")
        self.assertEqual(item["target_support_tier"], "reference_only")
        self.assertEqual(item["priority"], "P2")

    def test_classify_reference_only_us_as_structural_dcf_base_batch(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "F",
                "name": "Ford Motor Company",
                "method_group": "系统化量化",
                "pool": "signal_pool",
                "valuation_source": "target_mean_price",
                "valuation_support_tier": "reference_only",
                "trust_bucket": "watch",
                "trust_grade": "C",
                "suggested_action": "keep_in_watch_pool",
            },
            real_row={"valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
            signal_row={"market": "US", "signal_id": "s8", "as_of_date": "2026-03-14"},
            dcf_gap_batch_meta={"batch_kind": "structural_dcf_base", "reason": "no financial shell model and valuation_mode=parameterized_only"},
        )
        self.assertEqual(item["upgrade_lane"], "structural_dcf_base_batch")
        self.assertEqual(item["issue_type"], "structural_dcf_base_blocked")
        self.assertEqual(item["target_support_tier"], "formal_support")
        self.assertEqual(item["priority"], "P1")

    def test_classify_price_fallback_with_upgraded_real_source_as_refresh_reissue(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "AES",
                "name": "AES",
                "method_group": "系统化量化",
                "pool": "signal_pool",
                "valuation_source": "close_fallback",
                "valuation_support_tier": "price_fallback",
                "trust_bucket": "noisy",
                "trust_grade": "D",
                "suggested_action": "send_to_review_queue",
            },
            real_row={
                "valuation_source": "target_mean_price",
                "valuation_source_detail": "target_mean_price(stock_data_hub:yfinance)",
            },
            signal_row={"market": "US"},
        )
        self.assertEqual(item["upgrade_lane"], "signal_refresh_reissue")
        self.assertEqual(item["target_support_tier"], "reference_only")
        self.assertEqual(item["priority"], "P0")

    def test_classify_price_fallback_unresolved_as_external_prefetch(self) -> None:
        item = classify_gap_item(
            {
                "ticker": "AES",
                "name": "AES",
                "method_group": "系统化量化",
                "pool": "signal_pool",
                "valuation_source": "close_fallback",
                "valuation_support_tier": "price_fallback",
                "trust_bucket": "noisy",
                "trust_grade": "D",
                "suggested_action": "send_to_review_queue",
            },
            real_row={"valuation_source": "close_fallback", "valuation_source_detail": "close_fallback(dcf_symbol_unavailable)"},
            signal_row={"market": "US"},
        )
        self.assertEqual(item["upgrade_lane"], "external_valuation_prefetch")
        self.assertEqual(item["target_support_tier"], "reference_only")
        self.assertEqual(item["priority"], "P0")

    def test_build_backlog_summary(self) -> None:
        original = backlog_module.diagnose_dcf_gap_batch
        backlog_module.diagnose_dcf_gap_batch = lambda ticker, name='': {"batch_kind": "dcf_focus_expansion"}
        try:
            doc = build_source_upgrade_backlog(
                coverage_doc={
                    "as_of_date": "2026-03-05",
                    "signal_pool": {"count": 2, "valuation_support_breakdown": {"reference_only": 1, "price_fallback": 1}},
                    "gap_rows": [
                        {
                            "ticker": "600919.SS",
                            "name": "江苏银行",
                            "method_group": "宏观周期",
                            "pool": "signal_pool",
                            "valuation_source": "target_mean_price",
                            "valuation_support_tier": "reference_only",
                            "trust_bucket": "watch",
                            "trust_grade": "C",
                            "suggested_action": "keep_in_watch_pool",
                        },
                        {
                            "ticker": "AES",
                            "name": "AES",
                            "method_group": "系统化量化",
                            "pool": "signal_pool",
                            "valuation_source": "close_fallback",
                            "valuation_support_tier": "price_fallback",
                            "trust_bucket": "noisy",
                            "trust_grade": "D",
                            "suggested_action": "send_to_review_queue",
                        },
                    ],
                },
                real_rows=[
                    {"ticker": "600919.SS", "valuation_source": "target_mean_price", "valuation_source_detail": "yahoo_target_mean_price(dcf_symbol_unavailable)"},
                    {"ticker": "AES", "valuation_source": "target_mean_price", "valuation_source_detail": "target_mean_price(stock_data_hub:yfinance)"},
                ],
                signals=[
                    {"ticker": "600919.SS", "market": "A", "signal_id": "s1", "as_of_date": "2026-03-05"},
                    {"ticker": "AES", "market": "US", "signal_id": "s2", "as_of_date": "2026-03-05"},
                ],
            )
            self.assertEqual(doc["summary"]["gap_count"], 2)
            self.assertEqual(doc["summary"]["priority_breakdown"]["P0"], 1)
            self.assertEqual(doc["summary"]["priority_breakdown"]["P1"], 1)
            self.assertEqual(doc["summary"]["lane_breakdown"]["dcf_focus_expansion"], 1)
            self.assertEqual(doc["summary"]["lane_breakdown"]["signal_refresh_reissue"], 1)
            self.assertAlmostEqual(doc["summary"]["target_signal_formal_coverage_rate_if_done"], 0.5)
            self.assertAlmostEqual(doc["summary"]["target_signal_formal_or_reference_coverage_rate_if_done"], 1.0)
        finally:
            backlog_module.diagnose_dcf_gap_batch = original


if __name__ == "__main__":
    unittest.main()
