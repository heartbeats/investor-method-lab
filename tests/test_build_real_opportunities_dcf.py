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
                        consensus_fair_value=None,
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

    def test_build_dcf_subprocess_env_for_loopback_base_url(self) -> None:
        with mock.patch.dict(
            mod.os.environ,
            {
                "HTTP_PROXY": "http://127.0.0.1:7897",
                "HTTPS_PROXY": "http://127.0.0.1:7897",
                "NO_PROXY": "10.0.0.0/8",
            },
            clear=False,
        ):
            env = mod._build_dcf_subprocess_env("http://127.0.0.1:8000")
        self.assertIsNotNone(env)
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertIn("127.0.0.1", env.get("NO_PROXY", ""))
        self.assertIn("localhost", env.get("NO_PROXY", ""))
        self.assertIn("::1", env.get("NO_PROXY", ""))

    def test_build_dcf_subprocess_env_for_remote_base_url(self) -> None:
        env = mod._build_dcf_subprocess_env("https://example.com")
        self.assertIsNone(env)

    def test_apply_hub_comps_overlay_fills_missing_crosscheck(self) -> None:
        row = _sample_row("AAPL", close=100.0, target_mean=120.0)
        peer1 = _sample_row("MSFT", close=90.0, target_mean=110.0)
        peer2 = _sample_row("GOOGL", close=80.0, target_mean=100.0)

        row.dcf_symbol = "US.AAPL"
        row.valuation_source = "dcf_iv_base"
        row.dcf_quality_gate_status = "review"
        peer1.dcf_symbol = "US.MSFT"
        peer2.dcf_symbol = "US.GOOGL"

        with mock.patch.object(mod, "_stock_data_hub_url", return_value="http://127.0.0.1:18000"), mock.patch.object(
            mod,
            "_hub_post_json",
            return_value={
                "items": [
                    {
                        "symbol": "US.AAPL",
                        "status": "warn",
                        "metrics": {"trailing_pe": {"deviation_pct": 0.42}},
                    }
                ],
                "failed": {},
            },
        ):
            meta = mod.apply_hub_comps_overlay([row, peer1, peer2])

        self.assertTrue(meta["enabled"])
        self.assertEqual(row.dcf_comps_crosscheck_status, "warn")
        self.assertAlmostEqual(row.dcf_comps_deviation_vs_median or 0.0, 0.42, places=4)
        self.assertEqual(row.dcf_comps_source, "stock_data_hub_comps_baseline")
        self.assertAlmostEqual(row.dcf_quality_penalty_multiplier, 0.836, places=3)

    def test_apply_hub_comps_overlay_keeps_existing_crosscheck(self) -> None:
        row = _sample_row("AAPL", close=100.0, target_mean=120.0)
        peer1 = _sample_row("MSFT", close=90.0, target_mean=110.0)
        peer2 = _sample_row("GOOGL", close=80.0, target_mean=100.0)
        row.dcf_symbol = "US.AAPL"
        row.dcf_comps_crosscheck_status = "ok"
        row.dcf_comps_source = "dcf_internal"
        peer1.dcf_symbol = "US.MSFT"
        peer2.dcf_symbol = "US.GOOGL"

        with mock.patch.object(mod, "_stock_data_hub_url", return_value="http://127.0.0.1:18000"), mock.patch.object(
            mod,
            "_hub_post_json",
            return_value={"items": [], "failed": {}},
        ):
            meta = mod.apply_hub_comps_overlay([row, peer1, peer2])

        self.assertTrue(meta["enabled"])
        self.assertGreaterEqual(meta["skipped_existing_count"], 1)
        self.assertEqual(row.dcf_comps_crosscheck_status, "ok")
        self.assertEqual(row.dcf_comps_source, "dcf_internal")

    def test_apply_hub_comps_overlay_accepts_normalized_symbol_from_hub(self) -> None:
        row = _sample_row("AAPL", close=100.0, target_mean=120.0)
        peer1 = _sample_row("MSFT", close=90.0, target_mean=110.0)
        peer2 = _sample_row("AMZN", close=80.0, target_mean=100.0)

        with mock.patch.object(mod, "_stock_data_hub_url", return_value="http://127.0.0.1:18000"), mock.patch.object(
            mod,
            "_hub_post_json",
            return_value={
                "items": [
                    {
                        "symbol": "US.AAPL",
                        "status": "ok",
                        "metrics": {"trailing_pe": {"deviation_pct": 0.08}},
                    }
                ],
                "failed": {},
            },
        ):
            meta = mod.apply_hub_comps_overlay([row, peer1, peer2])

        self.assertTrue(meta["enabled"])
        self.assertEqual(row.dcf_comps_crosscheck_status, "ok")
        self.assertAlmostEqual(row.dcf_comps_deviation_vs_median or 0.0, 0.08, places=4)

    def test_build_hub_comps_batch_items_sector_size_prefers_sector_then_size(self) -> None:
        aapl = _sample_row("AAPL")
        msft = _sample_row("MSFT")
        tsla = _sample_row("TSLA")
        xom = _sample_row("XOM")
        aapl.dcf_symbol = "US.AAPL"
        msft.dcf_symbol = "US.MSFT"
        tsla.dcf_symbol = "US.TSLA"
        xom.dcf_symbol = "US.XOM"
        aapl.sector = "Technology"
        msft.sector = "Technology"
        tsla.sector = "Automotive"
        xom.sector = "Energy"

        items, _symbol_to_row, _skipped = mod._build_hub_comps_batch_items(
            [aapl, msft, tsla, xom],
            max_peers=2,
            min_peers=1,
            peer_strategy="sector_size",
            market_caps={
                "US.AAPL": 100.0,
                "US.MSFT": 110.0,
                "US.TSLA": 95.0,
                "US.XOM": 1000.0,
            },
        )
        item_by_symbol = {str(item["symbol"]): item for item in items}
        self.assertIn("US.AAPL", item_by_symbol)
        peers = item_by_symbol["US.AAPL"]["peers"]
        self.assertEqual(peers[0], "US.MSFT")
        self.assertEqual(peers[1], "US.TSLA")

    def test_apply_hub_comps_overlay_sector_size_sets_meta(self) -> None:
        row = _sample_row("AAPL")
        peer1 = _sample_row("MSFT")
        peer2 = _sample_row("AMZN")

        with mock.patch.object(mod, "_stock_data_hub_url", return_value="http://127.0.0.1:18000"), mock.patch.dict(
            mod.os.environ,
            {"IML_HUB_COMPS_PEER_STRATEGY": "sector_size", "IML_HUB_COMPS_PEER_MIN": "1"},
            clear=False,
        ), mock.patch.object(
            mod,
            "_hub_post_json",
            side_effect=[
                {
                    "items": [
                        {"symbol": "US.AAPL", "market_cap": 100.0},
                        {"symbol": "US.MSFT", "market_cap": 120.0},
                        {"symbol": "US.AMZN", "market_cap": 90.0},
                    ],
                    "failed": {},
                },
                {
                    "items": [
                        {"symbol": "US.AAPL", "status": "ok", "metrics": {"trailing_pe": {"deviation_pct": 0.02}}}
                    ],
                    "failed": {},
                },
            ],
        ) as mocked_post:
            meta = mod.apply_hub_comps_overlay([row, peer1, peer2])

        self.assertEqual(mocked_post.call_count, 2)
        self.assertEqual(meta["peer_strategy"], "sector_size")
        self.assertGreater(meta["market_cap_covered_count"], 0)
        self.assertGreater(meta["market_cap_coverage_ratio"], 0.0)
        self.assertEqual(row.dcf_comps_crosscheck_status, "ok")


if __name__ == "__main__":
    unittest.main()
