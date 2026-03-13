from __future__ import annotations

import importlib.util
import unittest
from types import SimpleNamespace
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_dcf_coverage_from_universe.py"
SPEC = importlib.util.spec_from_file_location("seed_dcf_coverage_from_universe", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SeedDCFCoverageFromUniverseTests(unittest.TestCase):
    def test_build_company_profile_uses_yfinance_when_available(self) -> None:
        original_fetch = MODULE.fetch_company_profile_from_yfinance
        try:
            MODULE.fetch_company_profile_from_yfinance = lambda symbol: {
                "name": "浦发银行",
                "currency": "CNY",
                "shares": 29352000000.0,
            }
            company, source = MODULE.build_company_profile(
                service=object(),
                symbol="SH.600000",
                name_hint="浦发银行",
                policy_id="anchored-cn-us-stable-r085-g3",
            )
        finally:
            MODULE.fetch_company_profile_from_yfinance = original_fetch

        self.assertEqual(company.symbol, "SH.600000")
        self.assertEqual(company.name, "浦发银行")
        self.assertEqual(company.currency, "CNY")
        self.assertEqual(company.shares, 29352000000.0)
        self.assertEqual(source, "yfinance")

    def test_build_company_profile_falls_back_to_ths_for_a_share(self) -> None:
        original_fetch = MODULE.fetch_company_profile_from_yfinance
        original_ths = MODULE.build_a_share_company_profile_from_ths
        fake_company = MODULE.CompanyProfile(
            symbol="SH.600000",
            name="浦发银行",
            currency="CNY",
            shares=29352000000.0,
            fx_rate=1.0,
            active_policy_id="anchored-cn-us-stable-r085-g3",
            growth_scenarios=MODULE.GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
        )
        try:
            def raise_rate_limit(symbol: str):
                raise RuntimeError("rate limited")

            MODULE.fetch_company_profile_from_yfinance = raise_rate_limit
            MODULE.build_a_share_company_profile_from_ths = lambda **kwargs: fake_company
            company, source = MODULE.build_company_profile(
                service=object(),
                symbol="SH.600000",
                name_hint="浦发银行",
                policy_id="anchored-cn-us-stable-r085-g3",
            )
        finally:
            MODULE.fetch_company_profile_from_yfinance = original_fetch
            MODULE.build_a_share_company_profile_from_ths = original_ths

        self.assertEqual(company.symbol, "SH.600000")
        self.assertEqual(company.shares, 29352000000.0)
        self.assertEqual(source, "ths_company_profile")


    def test_build_company_profile_falls_back_to_runtime_shell_placeholder_for_a_share_financial_template(self) -> None:
        original_fetch = MODULE.fetch_company_profile_from_yfinance
        original_ths = MODULE.build_a_share_company_profile_from_ths

        class FakeService:
            def _hub_stock_profiles_index(self):
                return {}

            def _map_lookup_with_alias(self, index, symbol):
                return {"industry": "Banks - Regional", "sector": "金融"}

            def _resolve_parameter_library(self, **kwargs):
                return {
                    "financial_template_family_id": "bank_ri_or_bank_multistage",
                    "financial_template_family_shell_model": "ri",
                }

        try:
            def raise_rate_limit(symbol: str):
                raise RuntimeError("rate limited")

            MODULE.fetch_company_profile_from_yfinance = raise_rate_limit
            MODULE.build_a_share_company_profile_from_ths = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("akshare unavailable"))
            company, source = MODULE.build_company_profile(
                service=FakeService(),
                symbol="SH.600919",
                name_hint="江苏银行",
                policy_id="company-auto-calibrated:SH.600919:v2",
            )
        finally:
            MODULE.fetch_company_profile_from_yfinance = original_fetch
            MODULE.build_a_share_company_profile_from_ths = original_ths

        self.assertEqual(company.symbol, "SH.600919")
        self.assertEqual(company.name, "江苏银行")
        self.assertEqual(company.currency, "CNY")
        self.assertEqual(company.shares, 1.0)
        self.assertEqual(source, "financial_template_placeholder")


    def test_seed_a_share_with_ths_fallback_uses_relaxed_normalization_strategy(self) -> None:
        calls = []
        original_approve = MODULE.approve_and_calculate

        class FakeRepo:
            def upsert_company(self, company):
                self.company = company

        class FakeService:
            def _load_financial_inputs_from_ths(self, **kwargs):
                return (
                    SimpleNamespace(
                        fiscal_year=2024,
                        fcf_reported=[3975143400.0, -696939200.0, -293556400.0],
                        cash=3220000000.0,
                        short_term_investments=0.0,
                        interest_bearing_debt=2040000000.0,
                    ),
                    401000000.0,
                    {"normalization_strategy": {"method": "mean", "window_years": 5, "apply_peak_guard": False}},
                )

            def update_financials(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(snapshot_id="snap-1")

        try:
            MODULE.approve_and_calculate = lambda **kwargs: (SimpleNamespace(snapshot_id="snap-1"), SimpleNamespace(iv_base=39.8, mos_base=-5.4))
            reviewed, valuation, strategy_label = MODULE.seed_a_share_with_ths_fallback(
                service=FakeService(),
                repo=FakeRepo(),
                existing_companies={},
                symbol="SH.688506",
                name_hint="百利天恒",
                policy_ids={"anchored-cn-us-stable-r085-g3"},
                operator="tester",
            )
        finally:
            MODULE.approve_and_calculate = original_approve

        self.assertEqual(reviewed.snapshot_id, "snap-1")
        self.assertEqual(valuation.iv_base, 39.8)
        self.assertEqual(strategy_label, "ths_primary:mean:w5:relaxed")
        self.assertEqual(calls[0]["normalization_method"], "mean")
        self.assertEqual(calls[0]["normalization_window_years"], 5)
        self.assertFalse(calls[0]["apply_peak_guard"])


if __name__ == "__main__":
    unittest.main()

