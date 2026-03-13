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

from investor_method_lab.opportunity_trust_chain import build_trust_outputs


class OpportunityTrustChainTest(unittest.TestCase):
    def _contracts(self) -> dict:
        return {
            "trust_standard": {
                "purpose": "trust standard",
                "formula": {
                    "weights": {
                        "source_authenticity": 0.4,
                        "traceability": 0.25,
                        "cross_source_consistency": 0.2,
                        "freshness": 0.15,
                    }
                },
                "dimensions": {
                    "traceability": {
                        "subscores": {
                            "source_system": 20,
                            "source_file_or_api": 20,
                            "updated_at": 20,
                            "cache_ttl": 15,
                            "verified_status": 15,
                            "truth_level": 10,
                        }
                    }
                },
            },
            "review_standard": {"purpose": "review standard"},
            "field_rules": {
                "focus_dashboard.price": {
                    "label": "当前价",
                    "domain": "quote_data",
                    "primary_source": {"A": "futu_opend", "US": "yahoo_finance"},
                    "backup_sources": {"A": ["akshare"], "US": ["fmp"]},
                    "reference_sources": ["alpha_vantage"],
                    "freshness_sla_hours": 24,
                    "cross_check_rule": "price_or_valuation",
                },
                "focus_dashboard.fv50": {
                    "label": "中性估值",
                    "domain": "valuation",
                    "primary_source": "local_dcf_snapshot",
                    "backup_sources": ["dcf_engine_result_cache"],
                    "reference_sources": ["external_valuation_cache"],
                    "freshness_sla_hours": 24,
                    "cross_check_rule": "multiple_or_financial",
                },
                "opportunities.best_reason": {
                    "label": "机会原因",
                    "domain": "opportunity_generation",
                    "primary_source": "method_decision_trace",
                    "backup_sources": ["opportunity_csv_snapshot"],
                    "reference_sources": [],
                    "freshness_sla_hours": 24,
                    "cross_check_rule": "non_empty_and_consistent_method_id",
                },
            },
            "source_whitelist": {
                "domains": {
                    "quote_data": {
                        "A": {"P1": ["futu_opend", "local_verified_cache"], "P2": ["yahoo_finance"], "P3": []},
                        "US": {"P1": ["yahoo_finance", "fmp", "local_verified_cache"], "P2": ["alpha_vantage"], "P3": []},
                    }
                }
            },
            "anomaly_standard": {
                "auto_escalation_triggers": [
                    "new_source_first_time_acceptance",
                    "high_grade_source_conflict",
                    "cross_module_field_inconsistency",
                    "trust_score_abrupt_jump",
                ]
            },
            "benchmark_mapping": {},
        }

    def _signal(self, *, ticker: str, symbol: str, market: str, valuation_source: str, review_state: str, review_reason: str, signal_id: str) -> dict:
        return {
            "signal_id": signal_id,
            "signal_generated_at_utc": "2026-03-05T01:00:00+00:00",
            "as_of_date": "2026-03-04",
            "ticker": ticker,
            "symbol": symbol,
            "market": market,
            "name": ticker,
            "method_group": "宏观周期",
            "method_group_id": "macro_regime",
            "entry_reason_summary": "催化:25.4 | 趋势:21.2",
            "price_at_signal": 20.34,
            "fair_value_at_signal": 22.0 if valuation_source != "close_fallback" else 20.34,
            "valuation_source_at_signal": valuation_source,
            "valuation_source_detail_at_signal": "yahoo_target_mean_price(dcf_symbol_unavailable)" if valuation_source == "target_mean_price" else "close_fallback(dcf_symbol_unavailable)",
            "primary_benchmark": {"benchmark_id": "A_WIDE_CSI300" if market == "A" else "US_WIDE_SPX"},
            "secondary_benchmark": {"benchmark_id": "A_WIDE_CSI300" if market == "A" else "US_WIDE_SPX"},
            "exit_template_id": "macro_regime",
            "review_state": review_state,
            "review_reason": review_reason,
            "trace_summary": {"hard_fail_reasons": []},
            "snapshot_refs": {
                "artifacts": [
                    {"kind": "real_file", "path": "data/opportunities.real_3markets.csv", "exists": True},
                    {"kind": "trace_file", "path": "output/method_decision_trace_real_3markets.json", "exists": True},
                ],
                "meta_ref": {"generated_at_utc": "2026-03-05T00:00:00+00:00"},
            },
        }

    def test_reference_only_valuation_becomes_watch(self) -> None:
        signal = self._signal(
            ticker="601688.SS",
            symbol="SH.601688",
            market="A",
            valuation_source="target_mean_price",
            review_state="auto",
            review_reason="passed_default_gate",
            signal_id="s1",
        )
        position = {
            "signal_id": "s1",
            "ticker": "601688.SS",
            "market": "A",
            "status": "open",
            "validation_as_of_date": "2026-03-05",
            "price_history_source": "snapshot:SH.601688",
            "primary_excess_return": 0.01,
            "strategy_return_net": 0.01,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_dir = Path(tmp_dir) / "dt=2026-03-06"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            (snapshot_dir / "price_history.jsonl").write_text(
                json.dumps(
                    {
                        "symbol": "SH.601688",
                        "provider": "futu_opend",
                        "as_of": "2026-03-05T00:00:00+00:00",
                        "source_chain": ["futu_opend"],
                        "candles": [
                            {"ts": "2026-03-04T00:00:00+08:00", "open": 20.2, "high": 20.5, "low": 20.1, "close": 20.34},
                            {"ts": "2026-03-05T00:00:00+08:00", "open": 20.3, "high": 20.6, "low": 20.2, "close": 20.55},
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            outputs = build_trust_outputs(
                signals=[signal],
                positions=[position],
                contracts=self._contracts(),
                snapshot_root=Path(tmp_dir),
                snapshot_date="2026-03-06",
            )
        confidence = outputs["confidence"]["opportunities"][0]
        self.assertEqual(confidence["trust_bucket"], "watch")
        self.assertEqual(confidence["trust_grade"], "C")
        self.assertEqual(confidence["review_result"], "auto_pass_with_warning")
        self.assertFalse(confidence["formal_layer_eligible"])
        self.assertEqual(outputs["confidence"]["trust_bucket_breakdown"]["watch"], 1)

    def test_close_fallback_enters_noisy_review_queue(self) -> None:
        signal = self._signal(
            ticker="F",
            symbol="US.F",
            market="US",
            valuation_source="close_fallback",
            review_state="escalated",
            review_reason="valuation_source=close_fallback",
            signal_id="s2",
        )
        position = {
            "signal_id": "s2",
            "ticker": "F",
            "market": "US",
            "status": "pending_entry",
            "validation_as_of_date": "2026-03-05",
            "price_history_source": "stock_data_hub:US.F",
            "primary_excess_return": None,
            "strategy_return_net": None,
        }
        outputs = build_trust_outputs(
            signals=[signal],
            positions=[position],
            contracts=self._contracts(),
            snapshot_root=Path(tempfile.gettempdir()) / "nonexistent_snapshot_root",
            snapshot_date="2026-03-06",
        )
        confidence = outputs["confidence"]["opportunities"][0]
        self.assertEqual(confidence["trust_bucket"], "noisy")
        self.assertEqual(confidence["trust_grade"], "D")
        self.assertEqual(confidence["review_result"], "manual_escalation")
        self.assertIn("H2_inferred_or_fallback_only", confidence["hard_veto_reasons"])
        review_item = outputs["review_queue"]["queue_items"][0]
        self.assertEqual(review_item["priority"], "P1")
        self.assertIn("valuation_source=close_fallback", review_item["queue_reason_summary"])


if __name__ == "__main__":
    unittest.main()
