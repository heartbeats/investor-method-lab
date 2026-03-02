from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_real_opportunities.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_real_opportunities", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load build_real_opportunities.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _sample_row(ticker: str, close: float = 100.0, target_mean: float | None = 120.0):
    return mod.RawMarketRow(
        ticker=ticker,
        yf_ticker=ticker,
        name=ticker,
        sector="Tech",
        as_of_date="2026-03-02",
        close=close,
        fair_value=target_mean if target_mean is not None else close,
        target_mean_price=target_mean,
        return_on_equity=None,
        gross_margins=None,
        operating_margins=None,
        revenue_growth=None,
        earnings_growth=None,
        earnings_quarterly_growth=None,
        debt_to_equity=None,
        beta=None,
        analyst_count=None,
        recommendation_mean=None,
        ret_3m=None,
        ret_6m=None,
        ret_12m=None,
        dist_to_sma200=None,
        vol_1y=None,
        max_drawdown_1y=None,
        note="",
        base_note="sample",
    )


class BuildRealOpportunitiesDCFTest(unittest.TestCase):
    def test_dcf_symbol_candidates_hk(self) -> None:
        candidates = mod.dcf_symbol_candidates("3690.HK")
        self.assertIn("HK.03690", candidates)
        self.assertIn("HK.3690", candidates)

    def test_resolve_dcf_symbol_cn_and_us(self) -> None:
        self.assertEqual(mod.resolve_dcf_symbol("600519.SS"), "SH.600519")
        self.assertEqual(mod.resolve_dcf_symbol("AAPL"), "US.AAPL")
        resolved = mod.resolve_dcf_symbol("0700.HK", {"HK.00700"})
        self.assertEqual(resolved, "HK.00700")

    def test_apply_dcf_overlay_prefers_dcf_iv_base(self) -> None:
        row = _sample_row("AAPL", close=100.0, target_mean=120.0)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / "dcf_valuation_link.py"
            script_path.write_text("# placeholder\n", encoding="utf-8")
            companies_file = tmp_path / "companies.json"
            companies_file.write_text(
                json.dumps([{"symbol": "US.AAPL"}], ensure_ascii=False),
                encoding="utf-8",
            )

            with mock.patch.object(
                mod,
                "_pull_dcf_portfolio",
                return_value={
                    "US.AAPL": mod.DCFValuation(
                        symbol="US.AAPL",
                        iv_base=130.0,
                        price=100.0,
                        mos_base=0.3,
                        status="watch",
                        pulled_at="2026-03-02T00:00:00+00:00",
                    )
                },
            ):
                meta = mod.apply_dcf_overlay(
                    [row],
                    enable_dcf=True,
                    dcf_link_script=script_path,
                    dcf_companies_file=companies_file,
                    dcf_base_url="http://127.0.0.1:8000",
                    dcf_timeout=15.0,
                    dcf_strict=False,
                )

        self.assertEqual(row.valuation_source, "dcf_iv_base")
        self.assertAlmostEqual(row.fair_value, 130.0)
        self.assertIn("dcf_symbol=US.AAPL", row.note)
        self.assertEqual(meta["covered_tickers"], ["AAPL"])

    def test_apply_dcf_overlay_fallback_when_uncovered(self) -> None:
        row = _sample_row("MSFT", close=100.0, target_mean=115.0)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            companies_file = tmp_path / "companies.json"
            companies_file.write_text(
                json.dumps([{"symbol": "US.AAPL"}], ensure_ascii=False),
                encoding="utf-8",
            )
            meta = mod.apply_dcf_overlay(
                [row],
                enable_dcf=True,
                dcf_link_script=tmp_path / "missing.py",
                dcf_companies_file=companies_file,
                dcf_base_url="http://127.0.0.1:8000",
                dcf_timeout=15.0,
                dcf_strict=False,
            )

        self.assertEqual(row.valuation_source, "target_mean_price")
        self.assertAlmostEqual(row.fair_value, 115.0)
        self.assertIn("fv_source=target_mean_price", row.note)
        self.assertEqual(meta["covered_tickers"], [])


if __name__ == "__main__":
    unittest.main()
