from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "generate_top20_opportunity_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_top20_opportunity_pack", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load generate_top20_opportunity_pack.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


class GenerateTop20OpportunityPackTest(unittest.TestCase):
    def test_load_validation_positions_from_positions_payload(self) -> None:
        payload = {
            "positions": [
                {"ticker": "AAPL", "status": "open"},
                {"ticker": "MSFT", "status": "closed"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "positions.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            records = mod.load_validation_positions(path)
        self.assertEqual(sorted(records.keys()), ["AAPL", "MSFT"])
        self.assertEqual(records["AAPL"]["status"], "open")

    def test_annotate_pack_outputs_merges_validation_and_summaries(self) -> None:
        base_row = {
            "ticker": "AAPL",
            "name": "Apple",
            "sector": "Technology",
            "valuation_source": "dcf_iv_base",
            "fair_value": "130",
            "dcf_iv_base": "130",
            "target_mean_price": "120",
            "dcf_quality_gate_status": "caution",
            "dcf_comps_crosscheck_status": "warn",
        }
        top_rows = [dict(base_row)]
        group_top_rows = [
            (
                SimpleNamespace(id="value_quality_compound", name="价值质量复利"),
                [dict(base_row, group_score=88.5, reason="质量:23.2")],
            )
        ]
        diversified_rows = [dict(base_row)]
        tiered_group_rows = [dict(base_row, group_id="value_quality_compound", group_name="价值质量复利")]

        mod.annotate_pack_outputs(
            top_rows=top_rows,
            group_top_rows=group_top_rows,
            diversified_rows=diversified_rows,
            tiered_group_rows=tiered_group_rows,
            positions_by_ticker={
                "AAPL": {
                    "ticker": "AAPL",
                    "status": "open",
                    "hit": True,
                    "days_held": 5,
                    "primary_excess_return": 0.025,
                    "exit_reason": "mark_to_market",
                    "template_id": "dcf",
                    "validation_as_of_date": "2026-03-13",
                }
            },
            confidence_by_ticker={
                "AAPL": {
                    "trust_score": 89.35,
                    "trust_grade": "C",
                    "trust_bucket": "watch",
                    "review_result": "auto_pass_with_warning",
                    "formal_layer_eligible": False,
                }
            },
            lineage_by_ticker={
                "AAPL": {
                    "traceability_score": 100.0,
                    "provider_tiers": ["P1"],
                    "source_match_types": ["backup", "reference_only"],
                    "source_systems": ["snapshot_price_history"],
                }
            },
        )

        self.assertEqual(top_rows[0]["validation_status"], "open")
        self.assertEqual(top_rows[0]["validation_summary"], "open | 命中 | 超额+2.5% | 5d")
        self.assertEqual(top_rows[0]["valuation_summary"], "dcf_iv_base | DCF 130.00 | 外部 120.00")
        self.assertEqual(top_rows[0]["risk_summary"], "DCF质量:caution | 交叉验证:warn")
        self.assertEqual(top_rows[0]["confidence_summary"], "C(89.3) | watch | 非正式层 | auto_pass_with_warning")
        self.assertEqual(top_rows[0]["source_lineage_summary"], "追踪100 | backup/reference_only | P1")
        self.assertEqual(group_top_rows[0][1][0]["validation_as_of_date"], "2026-03-13")
        self.assertEqual(diversified_rows[0]["validation_status"], "open")
        self.assertEqual(tiered_group_rows[0]["validation_status"], "open")

    def test_annotate_pack_outputs_appends_manual_review_summary(self) -> None:
        row = {
            "ticker": "AAPL",
            "name": "Apple",
            "sector": "Technology",
            "valuation_source": "dcf_iv_base",
            "fair_value": "130",
            "dcf_iv_base": "130",
        }
        top_rows = [dict(row)]

        mod.annotate_pack_outputs(
            top_rows=top_rows,
            group_top_rows=[],
            diversified_rows=[],
            tiered_group_rows=[],
            positions_by_ticker={},
            confidence_by_ticker={
                "AAPL": {
                    "trust_score": 89.35,
                    "trust_grade": "C",
                    "trust_bucket": "watch",
                    "review_result": "auto_pass_with_warning",
                    "formal_layer_eligible": False,
                }
            },
            lineage_by_ticker={},
            review_writeback_by_ticker={
                "AAPL": {
                    "manual_review_decision": "通过",
                    "manual_action": "promote_to_pack",
                    "manual_note": "进入今日机会包",
                    "manual_reviewed_at": "2026-03-13T09:00:00+00:00",
                }
            },
        )

        self.assertEqual(top_rows[0]["manual_review_decision"], "通过")
        self.assertEqual(top_rows[0]["manual_review_action"], "promote_to_pack")
        self.assertEqual(top_rows[0]["manual_review_summary"], "人工通过 | 纳入机会包 | 进入今日机会包")
        self.assertEqual(
            top_rows[0]["confidence_summary"],
            "C(89.3) | watch | 非正式层 | auto_pass_with_warning | 人工通过 | 纳入机会包 | 进入今日机会包",
        )

    def test_load_confidence_and_lineage_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            confidence_path = Path(tmp) / "confidence.json"
            confidence_path.write_text(
                json.dumps({"opportunities": [{"ticker": "AAPL", "trust_grade": "B", "trust_score": 93.2}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            lineage_path = Path(tmp) / "lineage.json"
            lineage_path.write_text(
                json.dumps(
                    {
                        "fields": [
                            {"ticker": "AAPL", "traceability_score": 100, "observed_provider_tier": "P1", "source_match_type": "primary", "source_system": "snapshot"},
                            {"ticker": "AAPL", "traceability_score": 90, "observed_provider_tier": "P2", "source_match_type": "backup", "source_system": "cache"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            confidence = mod.load_confidence_records(confidence_path)
            lineage = mod.load_field_lineage_summaries(lineage_path)
        self.assertEqual(confidence["AAPL"]["trust_grade"], "B")
        self.assertAlmostEqual(lineage["AAPL"]["traceability_score"], 95.0)
        self.assertEqual(lineage["AAPL"]["provider_tiers"], ["P1", "P2"])


if __name__ == "__main__":
    unittest.main()
