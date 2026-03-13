from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.opportunity_validation import (
    build_history_loader,
    evaluate_signal,
    evaluate_signals,
    resolve_template_id,
    summarize_validation,
)


class OpportunityValidationTest(unittest.TestCase):
    def _rules(self) -> dict:
        return {
            "friction_costs": {
                "US": {"buy_total_cost": 0.001, "sell_total_cost": 0.001},
                "A": {"buy_total_cost": 0.0015, "sell_total_cost": 0.002},
                "HK": {"buy_total_cost": 0.0018, "sell_total_cost": 0.0018},
            },
            "method_templates": {
                "dcf": {"exit_priority": ["price_reaches_signal_fv50", "return_gte_25pct", "drawdown_lte_-15pct", "holding_days_gte_250"]},
                "market": {"exit_priority": ["return_gte_18pct", "drawdown_lte_-8pct", "holding_days_gte_60"]},
                "event": {"exit_priority": ["return_gte_15pct", "drawdown_lte_-8pct", "holding_days_gte_20"]},
                "investor_follow": {"exit_priority": ["return_gte_20pct", "drawdown_lte_-12pct", "holding_days_gte_120"]},
            },
            "minimum_viable_thresholds": {
                "opportunity_excess_return": {"op": "gt", "value": 0},
                "opportunity_hit_rate": {"op": "gte", "value": 0.55},
                "profit_loss_ratio": {"op": "gte", "value": 1.5},
                "max_drawdown": {"op": "lte", "value": 0.2},
                "valuation_realization_rate": {"op": "gte", "value": 0.4},
            },
        }

    def _history_loader(self, mapping: dict):
        def loader(symbol: str, _start: date, _end: date):
            return mapping.get(symbol, [])
        return loader

    def test_resolve_template_prefers_dcf_when_dcf_iv_present(self) -> None:
        signal = {"valuation_source_at_signal": "dcf_iv_base", "method_group_id": "value_quality_compound"}
        self.assertEqual(resolve_template_id(signal, self._rules()), "dcf")

    def test_pending_entry_when_no_next_trading_day(self) -> None:
        signal = {
            "signal_id": "s1",
            "ticker": "AAPL",
            "name": "Apple",
            "market": "US",
            "method_group": "价值质量复利",
            "method_group_id": "value_quality_compound",
            "as_of_date": "2026-03-05",
            "valuation_source_at_signal": "target_mean_price",
            "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
            "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
        }
        price_map = {
            "AAPL": [{"date": "2026-03-05", "open": 100, "high": 101, "low": 99, "close": 100}],
            "^GSPC": [{"date": "2026-03-05", "open": 5000, "high": 5010, "low": 4990, "close": 5005}],
        }
        result = evaluate_signal(signal, self._rules(), date(2026, 3, 5), history_loader=self._history_loader(price_map))
        self.assertEqual(result.status, "pending_entry")

    def test_market_template_closes_on_take_profit(self) -> None:
        signal = {
            "signal_id": "s2",
            "ticker": "MSFT",
            "name": "Microsoft",
            "market": "US",
            "method_group": "宏观周期",
            "method_group_id": "macro_regime",
            "as_of_date": "2026-03-04",
            "valuation_source_at_signal": "close_fallback",
            "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
            "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
        }
        price_map = {
            "MSFT": [
                {"date": "2026-03-04", "open": 100, "high": 100, "low": 100, "close": 100},
                {"date": "2026-03-05", "open": 101, "high": 125, "low": 100, "close": 121},
            ],
            "^GSPC": [
                {"date": "2026-03-04", "open": 5000, "high": 5000, "low": 5000, "close": 5000},
                {"date": "2026-03-05", "open": 5010, "high": 5020, "low": 5000, "close": 5015},
            ],
        }
        result = evaluate_signal(signal, self._rules(), date(2026, 3, 5), history_loader=self._history_loader(price_map))
        self.assertEqual(result.template_id, "market")
        self.assertEqual(result.status, "closed")
        self.assertEqual(result.exit_reason, "return_gte_18pct")
        self.assertIsNotNone(result.primary_excess_return)
        self.assertTrue(result.hit)

    def test_investor_follow_can_expire(self) -> None:
        signal = {
            "signal_id": "s3",
            "ticker": "BABA",
            "name": "Alibaba",
            "market": "US",
            "method_group": "价值质量复利",
            "method_group_id": "value_quality_compound",
            "as_of_date": "2026-01-01",
            "valuation_source_at_signal": "target_mean_price",
            "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
            "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
        }
        prices = [{"date": "2026-01-01", "open": 100, "high": 100, "low": 100, "close": 100}]
        for i in range(1, 122):
            prices.append({"date": f"2026-01-{i+1:02d}" if i < 30 else f"2026-02-{i-29:02d}" if i < 58 else f"2026-03-{i-57:02d}" if i < 89 else f"2026-04-{i-88:02d}", "open": 100, "high": 105, "low": 98, "close": 101})
        price_map = {"BABA": prices, "^GSPC": prices}
        result = evaluate_signal(signal, self._rules(), date(2026, 4, 30), history_loader=self._history_loader(price_map))
        self.assertIn(result.status, {"expired", "closed"})

    def test_summary_contains_method_group_metrics(self) -> None:
        positions = evaluate_signals(
            signals=[
                {
                    "signal_id": "s4",
                    "ticker": "MSFT",
                    "name": "Microsoft",
                    "market": "US",
                    "method_group": "宏观周期",
                    "method_group_id": "macro_regime",
                    "as_of_date": "2026-03-04",
                    "valuation_source_at_signal": "close_fallback",
                    "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                    "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                }
            ],
            validation_rules=self._rules(),
            validation_as_of_date=date(2026, 3, 5),
            history_loader=self._history_loader(
                {
                    "MSFT": [
                        {"date": "2026-03-04", "open": 100, "high": 100, "low": 100, "close": 100},
                        {"date": "2026-03-05", "open": 101, "high": 110, "low": 100, "close": 108},
                    ],
                    "^GSPC": [
                        {"date": "2026-03-04", "open": 5000, "high": 5000, "low": 5000, "close": 5000},
                        {"date": "2026-03-05", "open": 5005, "high": 5006, "low": 5000, "close": 5003},
                    ],
                }
            ),
        )
        summary = summarize_validation(positions, self._rules(), date(2026, 3, 5), Path("ledger.jsonl"))
        self.assertIn("宏观周期", summary["method_group_summary"])
        self.assertEqual(summary["status_breakdown"]["open"], 1)
        self.assertEqual(summary["valuation_support_breakdown"]["price_fallback"], 1)

    def test_snapshot_loader_prevents_false_pending_entry(self) -> None:
        signal = {
            "signal_id": "s5",
            "symbol": "SH.601688",
            "ticker": "601688.SS",
            "name": "华泰证券",
            "market": "A",
            "method_group": "宏观周期",
            "method_group_id": "macro_regime",
            "as_of_date": "2026-03-04",
            "valuation_source_at_signal": "close_fallback",
            "primary_benchmark": {"benchmark_id": "A_WIDE_CSI300"},
            "secondary_benchmark": {"benchmark_id": "A_WIDE_CSI300"},
        }
        price_payloads = [
            {
                "symbol": "SH.601688",
                "candles": [
                    {"ts": "2026-03-04T00:00:00+08:00", "open": 20.0, "high": 20.2, "low": 19.8, "close": 20.0},
                    {"ts": "2026-03-05T00:00:00+08:00", "open": 20.1, "high": 20.5, "low": 20.0, "close": 20.4},
                ],
            },
            {
                "symbol": "SH.000300",
                "candles": [
                    {"ts": "2026-03-04T00:00:00+08:00", "open": 4000, "high": 4010, "low": 3990, "close": 4000},
                    {"ts": "2026-03-05T00:00:00+08:00", "open": 4010, "high": 4020, "low": 4000, "close": 4012},
                ],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_dir = Path(tmp_dir) / "dt=2026-03-06"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_file = snapshot_dir / "price_history.jsonl"
            with snapshot_file.open("w", encoding="utf-8") as file:
                for payload in price_payloads:
                    file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            loader = build_history_loader(
                snapshot_root=Path(tmp_dir),
                snapshot_date="2026-03-06",
                hub_url="",
                allow_yfinance_fallback=False,
            )
            result = evaluate_signal(signal, self._rules(), date(2026, 3, 5), history_loader=loader)
        self.assertEqual(result.status, "open")
        self.assertEqual(result.entry_date, "2026-03-05")
        self.assertTrue(result.price_history_source.startswith("snapshot:"))
        self.assertIsNotNone(result.primary_excess_return)


if __name__ == "__main__":
    unittest.main()
