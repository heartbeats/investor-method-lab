from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from investor_method_lab.review_writeback import (
    build_backlog_items,
    build_review_payload,
    format_manual_review_summary,
    load_review_writeback,
    reviewed_items_by_ticker,
)


class ReviewWritebackTest(unittest.TestCase):
    def test_build_backlog_items_filters_followup_actions(self) -> None:
        reviewed = [
            {
                "signal_id": "sig-1",
                "ticker": "AAPL",
                "name": "Apple",
                "priority": "P1",
                "manual_review_decision": "通过",
                "manual_action": "promote_to_pack",
                "manual_note": "纳入正式机会包",
                "writeback_status": "written_back",
            },
            {
                "signal_id": "sig-2",
                "ticker": "MSFT",
                "name": "Microsoft",
                "priority": "P2",
                "manual_review_decision": "观察",
                "manual_action": "keep_in_watch_pool",
                "manual_note": "继续观察",
            },
        ]

        backlog = build_backlog_items(reviewed)

        self.assertEqual(len(backlog), 1)
        self.assertEqual(backlog[0]["ticker"], "AAPL")
        self.assertEqual(backlog[0]["action_label"], "纳入机会包")
        self.assertEqual(backlog[0]["status"], "todo")

    def test_reviewed_items_by_ticker_prefers_latest_item(self) -> None:
        payload = build_review_payload(
            source={"app_token": "app"},
            reviewed=[
                {
                    "signal_id": "old",
                    "ticker": "AAPL",
                    "name": "Apple",
                    "manual_review_decision": "观察",
                    "manual_action": "keep_in_watch_pool",
                    "manual_reviewed_at": "2026-03-12T09:00:00+00:00",
                },
                {
                    "signal_id": "new",
                    "ticker": "AAPL",
                    "name": "Apple",
                    "manual_review_decision": "通过",
                    "manual_action": "promote_to_pack",
                    "manual_reviewed_at": "2026-03-13T09:00:00+00:00",
                },
            ],
        )

        mapping = reviewed_items_by_ticker(payload)

        self.assertEqual(mapping["AAPL"]["signal_id"], "new")

    def test_format_manual_review_summary_renders_human_label(self) -> None:
        summary = format_manual_review_summary(
            {
                "manual_review_decision": "通过",
                "manual_action": "promote_to_pack",
                "manual_note": "进入今日机会包",
            }
        )

        self.assertEqual(summary, "人工通过 | 纳入机会包 | 进入今日机会包")

    def test_load_review_writeback_tolerates_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{not-json", encoding="utf-8")

            payload = load_review_writeback(path)

            self.assertEqual(payload["summary"]["reviewed_items_count"], 0)
            self.assertIn("invalid_json", payload["load_receipt"]["reason"])



if __name__ == "__main__":
    unittest.main()
