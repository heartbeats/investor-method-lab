from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_universe_core_3markets.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_universe_core_3markets", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_universe_core_3markets.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


class BuildUniverseCore3MarketsTest(unittest.TestCase):
    def test_load_focus_rows_includes_pdd_anchor(self) -> None:
        payload = {
            "symbols": [
                {"dcf_symbol": "US.PDD", "ticker": "PDD", "name": "拼多多"},
                {"dcf_symbol": "HK.00700", "ticker": "0700.HK", "name": "腾讯控股"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            focus_file = Path(tmp) / "focus.json"
            focus_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows = mod.load_focus_rows(focus_file)
        self.assertEqual([row.ticker for row in rows], ["PDD", "0700.HK"])
        self.assertEqual(rows[0].included_reason, "dcf_special_focus")

    def test_apply_seed_anchors_matches_hk_aliases(self) -> None:
        source = [
            mod.UniverseRow(
                ticker="00700.HK",
                market="HK",
                name="TENCENT",
                sector="Unknown",
                liquidity_tag="hk_shortsell_eligible",
                included_reason="hk_main_board",
                note="HK core",
            )
        ]
        anchors = [
            mod.UniverseRow(
                ticker="0700.HK",
                market="HK",
                name="Tencent Holdings",
                sector="Communication Services",
                liquidity_tag="special_focus_anchor",
                included_reason="dcf_special_focus",
                note="special focus",
            )
        ]
        rows = mod.apply_seed_anchors(source, anchors, "HK", 10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].ticker, "00700.HK")


if __name__ == "__main__":
    unittest.main()
