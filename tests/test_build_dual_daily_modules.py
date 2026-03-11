from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_dual_daily_modules.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_dual_daily_modules", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_dual_daily_modules.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


class BuildDualDailyModulesTest(unittest.TestCase):
    def test_dcf_symbol_to_ticker(self) -> None:
        self.assertEqual(mod.dcf_symbol_to_ticker("US.GOOGL"), "GOOGL")
        self.assertEqual(mod.dcf_symbol_to_ticker("HK.00700"), "0700.HK")
        self.assertEqual(mod.dcf_symbol_to_ticker("HK.03690"), "3690.HK")
        self.assertEqual(mod.dcf_symbol_to_ticker("SH.600519"), "600519.SS")
        self.assertEqual(mod.dcf_symbol_to_ticker("SZ.000858"), "000858.SZ")

    def test_load_focus_items_from_dict_file(self) -> None:
        payload = {
            "symbols": [
                {"dcf_symbol": "US.AAPL", "ticker": "AAPL", "name": "Apple"},
                {"dcf_symbol": "US.AAPL", "ticker": "AAPL", "name": "Apple Dup"},
                {"dcf_symbol": "HK.00700", "name": "Tencent"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            focus_file = Path(tmp) / "focus.json"
            focus_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows = mod.load_focus_items(focus_file=focus_file, dcf_targets_file=Path(tmp) / "none.json")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].dcf_symbol, "US.AAPL")
        self.assertEqual(rows[1].ticker, "0700.HK")

    def test_build_opportunity_rows_excludes_focus_and_sorts(self) -> None:
        top_rows = [
            {
                "ticker": "AAPL",
                "name": "Apple",
                "composite_score": "70.5",
                "margin_of_safety": "12.0",
                "best_group": "价值质量复利",
                "note": "close=100 | target=120",
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft",
                "composite_score": "85.1",
                "margin_of_safety": "18.0",
                "best_group": "宏观周期",
                "note": "close=200 | target=250",
            },
            {
                "ticker": "0700.HK",
                "name": "Tencent",
                "composite_score": "90.0",
                "margin_of_safety": "20.0",
                "best_group": "深度价值修复",
                "note": "close=300 | target=360",
            },
        ]
        rows = mod.build_opportunity_rows(top_rows, focus_tickers={"AAPL", "0700.HK"}, top_n=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticker"], "MSFT")

    def test_build_focus_rows_matches_hk_aliases(self) -> None:
        focus_items = [mod.FocusItem(dcf_symbol="HK.00700", ticker="0700.HK", name="腾讯控股", tag="manual")]
        real_map = {
            "00700.HK": {
                "ticker": "00700.HK",
                "dcf_symbol": "HK.00700",
                "name": "Tencent Holdings",
                "note": "close=553.50 | target=600.00",
                "target_mean_price": "600.0",
            }
        }
        rows, missing = mod.build_focus_rows(focus_items, real_map)
        self.assertEqual(len(rows), 1)
        self.assertFalse(missing)
        self.assertEqual(rows[0]["name"], "Tencent Holdings")

    def test_ticker_lookup_keys_covers_hk_variants(self) -> None:
        keys = mod.ticker_lookup_keys("0700.HK")
        self.assertIn("0700.HK", keys)
        self.assertIn("00700.HK", keys)
        self.assertIn("HK.00700", keys)


if __name__ == "__main__":
    unittest.main()
