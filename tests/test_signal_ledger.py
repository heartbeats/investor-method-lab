from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.signal_ledger import (
    append_signal_entries,
    build_latest_summary,
    build_refresh_reissue_entries,
    build_signal_entries,
    load_benchmark_config,
    load_existing_signal_ids,
)


class SignalLedgerTest(unittest.TestCase):
    def _benchmark_config(self) -> dict:
        return load_benchmark_config(path=None)

    def test_build_signal_entries_filters_focus_and_freezes_core_fields(self) -> None:
        top_rows = [
            {
                "ticker": "AAPL",
                "name": "Apple",
                "sector": "Unknown",
                "composite_score": "88.2",
                "best_group": "价值质量复利",
                "best_reason": "安全边际:20.0 | 质量:25.0",
                "margin_of_safety": "20.0",
                "risk_control": "75.0",
                "note": "US core | real-data@2026-03-13 | close=200 | target=250 | fv_source=target_mean_price | upside=25.0%",
                "market": "US",
                "explain_best_group_id": "value_quality_compound",
                "explain_group_trace_json": json.dumps([
                    {
                        "group_id": "value_quality_compound",
                        "tier": "core",
                        "tier_reason": "通过硬筛",
                        "hard_pass": True,
                        "near_miss": False,
                        "weighted_contribution": 12.3,
                        "base_score": 80.0,
                        "adjusted_score": 75.0,
                        "hard_fail_reasons": [],
                        "soft_penalties": [],
                    }
                ], ensure_ascii=False),
            },
            {
                "ticker": "0700.HK",
                "name": "Tencent",
                "sector": "Unknown",
                "composite_score": "80.1",
                "best_group": "宏观周期",
                "best_reason": "催化:18.0 | 趋势:15.0",
                "margin_of_safety": "5.0",
                "risk_control": "55.0",
                "note": "HK core | real-data@2026-03-13 | close=300 | target=320 | fv_source=target_mean_price | upside=6.7%",
                "market": "HK",
                "explain_best_group_id": "macro_regime",
                "explain_group_trace_json": "[]",
            },
        ]
        real_rows = [
            {
                "ticker": "AAPL",
                "name": "Apple",
                "sector": "Unknown",
                "fair_value": "250",
                "valuation_source": "target_mean_price",
                "valuation_source_detail": "yahoo_target_mean_price",
                "dcf_symbol": "US.AAPL",
                "dcf_quality_gate_status": "",
                "note": "US core | real-data@2026-03-13 | close=200 | target=250 | fv_source=target_mean_price | upside=25.0%",
            }
        ]
        trace_payload = {
            "rulebook_version": "v4-test",
            "rows": [
                {
                    "ticker": "AAPL",
                    "market": "US",
                    "groups": [
                        {
                            "group_id": "value_quality_compound",
                            "tier": "core",
                            "tier_reason": "通过硬筛",
                            "hard_pass": True,
                            "near_miss": False,
                        }
                    ],
                }
            ],
        }
        meta_payload = {
            "as_of_dates": ["2026-03-13"],
            "generated_at_utc": "2026-03-13T01:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = {
                "top_file": root / "top.csv",
                "real_file": root / "real.csv",
                "trace_file": root / "trace.json",
                "meta_file": root / "meta.json",
            }
            for path, text in {
                paths["top_file"]: "top",
                paths["real_file"]: "real",
                paths["trace_file"]: "trace",
                paths["meta_file"]: "meta",
            }.items():
                path.write_text(text, encoding="utf-8")
            entries = build_signal_entries(
                top_rows=top_rows,
                real_rows=real_rows,
                trace_payload=trace_payload,
                meta_payload=meta_payload,
                benchmark_config=self._benchmark_config(),
                artifact_paths=paths,
                source_list_id="opportunity_mining_daily",
                focus_tickers={"0700.HK", "HK.00700"},
            )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["ticker"], "AAPL")
        self.assertEqual(entry["symbol"], "US.AAPL")
        self.assertEqual(entry["market"], "US")
        self.assertEqual(entry["strategy_version"], "top20_pack_v4::v4-test")
        self.assertEqual(entry["primary_benchmark"]["benchmark_id"], "US_WIDE_SPX")
        self.assertEqual(entry["secondary_benchmark"]["confidence"], "fallback_to_primary")
        self.assertEqual(entry["review_state"], "auto")
        self.assertEqual(entry["exit_template_id"], "value_quality_compound")
        self.assertEqual(entry["price_at_signal"], 200.0)
        self.assertEqual(entry["fair_value_at_signal"], 250.0)

    def test_review_state_escalates_for_close_fallback(self) -> None:
        top_rows = [
            {
                "ticker": "MSFT",
                "name": "Microsoft",
                "sector": "Technology",
                "composite_score": "70.0",
                "best_group": "宏观周期",
                "best_reason": "催化:20.0 | 趋势:18.0",
                "margin_of_safety": "0.0",
                "risk_control": "50.0",
                "note": "US core | real-data@2026-03-13 | close=400 | target=400 | fv_source=close_fallback | upside=0.0%",
                "market": "US",
                "explain_best_group_id": "macro_regime",
                "explain_group_trace_json": "[]",
            }
        ]
        real_rows = [
            {
                "ticker": "MSFT",
                "name": "Microsoft",
                "sector": "Technology",
                "fair_value": "400",
                "valuation_source": "close_fallback",
                "valuation_source_detail": "close_fallback(test)",
                "dcf_symbol": "US.MSFT",
                "dcf_quality_gate_status": "",
                "note": "US core | real-data@2026-03-13 | close=400 | target=400 | fv_source=close_fallback | upside=0.0%",
            }
        ]
        entries = build_signal_entries(
            top_rows=top_rows,
            real_rows=real_rows,
            trace_payload={"rulebook_version": "v4", "rows": []},
            meta_payload={"as_of_dates": ["2026-03-13"]},
            benchmark_config=self._benchmark_config(),
            artifact_paths={},
            source_list_id="opportunity_mining_daily",
            focus_tickers=set(),
        )
        self.assertEqual(entries[0]["review_state"], "escalated")
        self.assertEqual(entries[0]["secondary_benchmark"]["benchmark_id"], "US_TECH_GROWTH")

    def test_build_refresh_reissue_entries_when_real_source_upgrades(self) -> None:
        ledger_entries = [
            {
                "signal_id": "sig-old",
                "signal_generated_at_utc": "2026-03-05T01:00:00+00:00",
                "source_list_id": "opportunity_mining_daily",
                "source_rank": 2,
                "as_of_date": "2026-03-05",
                "ticker": "AES",
                "symbol": "US.AES",
                "market": "US",
                "name": "AES Corporation",
                "sector": "Utilities",
                "method_group": "系统化量化",
                "method_group_id": "systematic_quant",
                "method_family": "系统化量化",
                "method_family_id": "systematic_quant",
                "strategy_version": "top20_pack_v4::v4",
                "signal_origin": "top_ranked_candidate",
                "entry_reason_summary": "old",
                "price_at_signal": 14.22,
                "fair_value_at_signal": 14.22,
                "margin_of_safety_at_signal": 0.0,
                "risk_control_at_signal": 50.0,
                "composite_score_at_signal": 70.0,
                "valuation_source_at_signal": "close_fallback",
                "valuation_source_detail_at_signal": "close_fallback(old)",
                "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                "exit_template_id": "systematic_quant",
                "review_state": "escalated",
                "review_reason": "valuation_source=close_fallback",
                "trace_summary": {},
                "snapshot_refs": {},
            }
        ]
        real_rows = [
            {
                "ticker": "AES",
                "name": "AES Corporation",
                "sector": "Utilities",
                "fair_value": "16.22",
                "valuation_source": "target_mean_price",
                "valuation_source_detail": "target_mean_price(stock_data_hub:yfinance)",
                "note": "US core | real-data@2026-03-12 | close=11.8 | target=16.22 | fv_source=target_mean_price | upside=37.4%",
            }
        ]
        refresh_entries = build_refresh_reissue_entries(
            ledger_entries=ledger_entries,
            current_batch_entries=[],
            real_rows=real_rows,
            meta_payload={"as_of_dates": ["2026-03-12"]},
            artifact_paths={},
            refresh_source_list_id="opportunity_mining_daily_refresh_reissue",
            focus_tickers=set(),
        )
        self.assertEqual(len(refresh_entries), 1)
        entry = refresh_entries[0]
        self.assertEqual(entry["signal_origin"], "refresh_reissue")
        self.assertEqual(entry["ticker"], "AES")
        self.assertEqual(entry["as_of_date"], "2026-03-12")
        self.assertEqual(entry["valuation_source_at_signal"], "target_mean_price")
        self.assertEqual(entry["previous_valuation_source_at_signal"], "close_fallback")
        self.assertEqual(entry["refresh_reissue_of_signal_id"], "sig-old")
        self.assertEqual(entry["review_state"], "auto")

    def test_build_refresh_reissue_entries_prefers_real_note_date_over_stale_meta(self) -> None:
        ledger_entries = [
            {
                "signal_id": "sig-old",
                "signal_generated_at_utc": "2026-03-12T01:00:00+00:00",
                "source_list_id": "opportunity_mining_daily",
                "source_rank": 2,
                "as_of_date": "2026-03-12",
                "ticker": "BLDR",
                "symbol": "US.BLDR",
                "market": "US",
                "name": "Builders FirstSource",
                "sector": "Industrials",
                "method_group": "系统化量化",
                "method_group_id": "systematic_quant",
                "method_family": "系统化量化",
                "method_family_id": "systematic_quant",
                "strategy_version": "top20_pack_v4::v4",
                "signal_origin": "refresh_reissue",
                "entry_reason_summary": "old",
                "price_at_signal": 88.09,
                "fair_value_at_signal": 127.28,
                "margin_of_safety_at_signal": 0.0,
                "risk_control_at_signal": 50.0,
                "composite_score_at_signal": 70.0,
                "valuation_source_at_signal": "target_mean_price",
                "valuation_source_detail_at_signal": "target_mean_price(stock_data_hub:yfinance)",
                "primary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                "secondary_benchmark": {"benchmark_id": "US_WIDE_SPX"},
                "exit_template_id": "systematic_quant",
                "review_state": "auto",
                "review_reason": "passed_default_gate",
                "trace_summary": {},
                "snapshot_refs": {},
            }
        ]
        real_rows = [
            {
                "ticker": "BLDR",
                "name": "Builders FirstSource",
                "sector": "Industrials",
                "fair_value": "382.03",
                "valuation_source": "dcf_iv_base",
                "valuation_source_detail": "US.BLDR:iv_base",
                "note": "US core | real-data@2026-03-14 | close=88.09 | target=127.29 | fv_source=dcf_iv_base | dcf_symbol=US.BLDR | dcf_iv=382.03 | upside=333.7%",
            }
        ]
        refresh_entries = build_refresh_reissue_entries(
            ledger_entries=ledger_entries,
            current_batch_entries=[],
            real_rows=real_rows,
            meta_payload={"as_of_dates": ["2026-03-12"]},
            artifact_paths={},
            refresh_source_list_id="opportunity_mining_daily_refresh_reissue",
            focus_tickers=set(),
        )
        self.assertEqual(len(refresh_entries), 1)
        self.assertEqual(refresh_entries[0]["as_of_date"], "2026-03-14")

    def test_append_only_dedup_and_summary(self) -> None:
        entry = {
            "signal_id": "sig-1",
            "as_of_date": "2026-03-13",
            "ticker": "AAPL",
            "name": "Apple",
            "method_group": "价值质量复利",
            "composite_score_at_signal": 80.0,
            "price_at_signal": 200.0,
            "fair_value_at_signal": 250.0,
            "valuation_source_at_signal": "target_mean_price",
            "review_state": "auto",
            "entry_reason_summary": "测试",
            "source_rank": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            append_signal_entries(ledger, [entry])
            self.assertEqual(load_existing_signal_ids(ledger), {"sig-1"})
            append_signal_entries(ledger, [])
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            summary = build_latest_summary(
                ledger_path=ledger,
                ledger_entries=rows,
                batch_entries=[entry],
                newly_appended_entries=[entry],
            )
        self.assertEqual(summary["total_signals"], 1)
        self.assertEqual(summary["latest_as_of_date"], "2026-03-13")
        self.assertEqual(summary["newly_appended_count"], 1)
        self.assertEqual(summary["latest_batch_review_state_breakdown"], {"auto": 1})
        self.assertEqual(summary["latest_batch_signal_origin_breakdown"], {"<empty>": 1})


if __name__ == "__main__":
    unittest.main()
