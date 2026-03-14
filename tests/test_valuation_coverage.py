from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from investor_method_lab.valuation_coverage import (
    append_history,
    build_valuation_coverage,
    history_snapshot_record,
    render_valuation_coverage_markdown,
)


class ValuationCoverageTests(unittest.TestCase):
    def test_build_valuation_coverage_rolls_up_support_tiers(self) -> None:
        real_rows = [
            {"ticker": "AAA", "name": "Alpha", "valuation_source": "dcf_iv_base"},
            {"ticker": "BBB", "name": "Beta", "valuation_source": "target_mean_price"},
            {"ticker": "CCC", "name": "Gamma", "valuation_source": "close_fallback"},
        ]
        signals = [
            {
                "signal_id": "s1",
                "ticker": "AAA",
                "name": "Alpha",
                "method_group": "价值质量复利",
                "valuation_source_at_signal": "dcf_external_consensus",
                "as_of_date": "2026-03-05",
            },
            {
                "signal_id": "s2",
                "ticker": "BBB",
                "name": "Beta",
                "method_group": "宏观周期",
                "valuation_source_at_signal": "close_fallback",
                "as_of_date": "2026-03-05",
            },
        ]
        positions = [
            {
                "signal_id": "s1",
                "ticker": "AAA",
                "status": "closed",
                "strategy_return_net": 0.12,
                "primary_excess_return": 0.08,
                "hit": True,
                "valuation_source_at_signal": "dcf_external_consensus",
                "valuation_support_tier": "formal_support",
            },
            {
                "signal_id": "s2",
                "ticker": "BBB",
                "status": "open",
                "strategy_return_net": 0.01,
                "primary_excess_return": 0.0,
                "hit": False,
                "valuation_source_at_signal": "close_fallback",
                "valuation_support_tier": "price_fallback",
            },
        ]
        confidence_payload = {
            "opportunities": [
                {
                    "signal_id": "s1",
                    "ticker": "AAA",
                    "valuation_source_at_signal": "dcf_external_consensus",
                    "trust_bucket": "watch",
                    "trust_grade": "B",
                    "suggested_action": "keep_in_watch_pool",
                },
                {
                    "signal_id": "s2",
                    "ticker": "BBB",
                    "valuation_source_at_signal": "close_fallback",
                    "trust_bucket": "noisy",
                    "trust_grade": "C",
                    "suggested_action": "upgrade_valuation_source",
                },
            ]
        }
        doc = build_valuation_coverage(
            real_rows=real_rows,
            signals=signals,
            positions=positions,
            focus_lookup={"AAA", "BBB"},
            meta_payload={"as_of_dates": ["2026-03-05"]},
            confidence_payload=confidence_payload,
            history_rows=[],
        )

        self.assertEqual(doc["overall_real_universe"]["valuation_support_breakdown"]["formal_core"], 1)
        self.assertEqual(doc["overall_real_universe"]["valuation_support_breakdown"]["reference_only"], 1)
        self.assertEqual(doc["overall_real_universe"]["valuation_support_breakdown"]["price_fallback"], 1)
        self.assertEqual(doc["focus_pool"]["count"], 2)
        self.assertEqual(doc["signal_pool"]["valuation_support_breakdown"]["formal_support"], 1)
        self.assertEqual(doc["signal_pool"]["valuation_support_breakdown"]["price_fallback"], 1)
        self.assertEqual(doc["validation_by_valuation_support"]["formal_support"]["closed_count"], 1)
        self.assertEqual(doc["validation_by_valuation_support"]["price_fallback"]["open_count"], 1)
        self.assertEqual(doc["confidence_by_valuation_support"]["formal_support"]["watch"], 1)
        self.assertEqual(doc["confidence_by_valuation_support"]["price_fallback"]["noisy"], 1)
        self.assertEqual(doc["gap_rows"][0]["pool"], "signal_pool")
        self.assertEqual(doc["gap_rows"][0]["ticker"], "BBB")

    def test_build_valuation_coverage_includes_manual_review_summary(self) -> None:
        review_payload = {
            "reviewed_items": [
                {
                    "signal_id": "s2",
                    "ticker": "BBB",
                    "name": "BBB Inc",
                    "manual_review_decision": "升级",
                    "manual_action": "upgrade_valuation_source",
                    "manual_note": "补高质量估值源",
                    "writeback_status": "written_back",
                }
            ]
        }
        doc = build_valuation_coverage(
            real_rows=[
                {"ticker": "AAA", "name": "AAA Inc", "valuation_source": "dcf_iv_base"},
                {"ticker": "BBB", "name": "BBB Inc", "valuation_source": "close_fallback"},
            ],
            signals=[
                {
                    "signal_id": "s2",
                    "ticker": "BBB",
                    "name": "BBB Inc",
                    "method_group": "宏观周期",
                    "valuation_source_at_signal": "close_fallback",
                    "as_of_date": "2026-03-05",
                }
            ],
            positions=[],
            focus_lookup={"BBB"},
            meta_payload={"as_of_dates": ["2026-03-05"]},
            confidence_payload={
                "opportunities": [
                    {"signal_id": "s2", "ticker": "BBB", "valuation_source_at_signal": "close_fallback", "trust_bucket": "noisy", "suggested_action": "upgrade_valuation_source"}
                ]
            },
            review_writeback_payload=review_payload,
            history_rows=[],
        )

        self.assertEqual(doc["manual_review"]["reviewed_items_count"], 1)
        self.assertEqual(doc["manual_review"]["followup_backlog_count"], 1)
        self.assertEqual(doc["gap_rows"][0]["manual_review_decision"], "升级")
        self.assertEqual(doc["gap_rows"][0]["manual_action"], "upgrade_valuation_source")
        markdown = render_valuation_coverage_markdown(doc)
        self.assertIn("人工复核闭环", markdown)
        self.assertIn("upgrade_valuation_source", markdown)


    def test_build_valuation_coverage_surfaces_review_sync_receipt(self) -> None:
        review_payload = {
            "reviewed_items": [],
            "sync_receipt": {
                "synced": False,
                "reason": "missing_feishu_credentials",
                "fallback_mode": "reuse_previous_snapshot",
            },
        }
        doc = build_valuation_coverage(
            real_rows=[],
            signals=[],
            positions=[],
            focus_lookup=set(),
            meta_payload={"as_of_dates": ["2026-03-05"]},
            review_writeback_payload=review_payload,
            history_rows=[],
        )

        self.assertEqual(doc["manual_review"]["sync_status"], "degraded")
        self.assertEqual(doc["manual_review"]["sync_reason"], "missing_feishu_credentials")
        markdown = render_valuation_coverage_markdown(doc)
        self.assertIn("拉取状态", markdown)
        self.assertIn("reuse_previous_snapshot", markdown)

    def test_signal_pool_uses_latest_signal_per_ticker(self) -> None:
        doc = build_valuation_coverage(
            real_rows=[{"ticker": "AES", "valuation_source": "target_mean_price"}],
            signals=[
                {
                    "signal_id": "old",
                    "ticker": "AES",
                    "name": "AES",
                    "method_group": "系统化量化",
                    "valuation_source_at_signal": "close_fallback",
                    "as_of_date": "2026-03-05",
                    "signal_generated_at_utc": "2026-03-05T01:00:00+00:00",
                },
                {
                    "signal_id": "new",
                    "ticker": "AES",
                    "name": "AES",
                    "method_group": "系统化量化",
                    "valuation_source_at_signal": "target_mean_price",
                    "as_of_date": "2026-03-12",
                    "signal_generated_at_utc": "2026-03-12T01:00:00+00:00",
                },
            ],
            positions=[],
            focus_lookup=set(),
            meta_payload={"as_of_dates": ["2026-03-12"]},
            confidence_payload={
                "opportunities": [
                    {"signal_id": "old", "ticker": "AES", "valuation_source_at_signal": "close_fallback", "trust_bucket": "noisy"},
                    {"signal_id": "new", "ticker": "AES", "valuation_source_at_signal": "target_mean_price", "trust_bucket": "watch"},
                ]
            },
            history_rows=[],
        )
        self.assertEqual(doc["signal_pool"]["count"], 1)
        self.assertEqual(doc["signal_pool"]["valuation_support_breakdown"]["reference_only"], 1)
        self.assertNotIn("price_fallback", doc["signal_pool"]["valuation_support_breakdown"])
        self.assertEqual(doc["confidence_by_valuation_support"]["reference_only"]["watch"], 1)

    def test_latest_as_of_date_prefers_newer_signal_date_when_meta_is_stale(self) -> None:
        doc = build_valuation_coverage(
            real_rows=[{"ticker": "BLDR", "valuation_source": "dcf_iv_base"}],
            signals=[
                {
                    "signal_id": "refresh",
                    "ticker": "BLDR",
                    "name": "Builders FirstSource",
                    "method_group": "系统化量化",
                    "valuation_source_at_signal": "dcf_iv_base",
                    "as_of_date": "2026-03-14",
                    "signal_generated_at_utc": "2026-03-14T01:00:00+00:00",
                },
            ],
            positions=[],
            focus_lookup=set(),
            meta_payload={"as_of_dates": ["2026-03-12"]},
            history_rows=[],
        )
        self.assertEqual(doc["as_of_date"], "2026-03-14")

    def test_history_append_dedupes_same_snapshot(self) -> None:
        record = history_snapshot_record(
            as_of_date="2026-03-05",
            universe_summary={
                "formal_valuation_coverage_rate": 0.4,
                "price_fallback_rate": 0.2,
            },
            focus_summary={
                "formal_valuation_coverage_rate": 0.5,
                "price_fallback_rate": 0.25,
            },
            signal_summary={
                "formal_valuation_coverage_rate": 0.6,
                "price_fallback_rate": 0.1,
            },
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            history_file = Path(tmp_dir) / "valuation_coverage_history.jsonl"
            append_history(history_file, record)
            append_history(history_file, record)
            lines = history_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
