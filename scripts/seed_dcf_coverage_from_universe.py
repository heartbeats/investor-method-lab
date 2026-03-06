#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UNIVERSE = PROJECT_ROOT / "data" / "opportunities.universe_3markets.csv"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "dcf_coverage_seed_report.json"
DEFAULT_DCF_ROOT = Path.home() / "codex-project"
DEFAULT_DCF_DATA_DIR = DEFAULT_DCF_ROOT / "data"

if str(DEFAULT_DCF_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_DCF_ROOT))

from dcf.models import CompanyProfile, GrowthScenarios  # noqa: E402
from dcf.repository_json import JSONRepository  # noqa: E402
from dcf.service import DCFService  # noqa: E402
from dcf.financial_ingest import fetch_company_profile_from_yfinance  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从三市场股票池自动补齐 DCF 覆盖")
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=DEFAULT_UNIVERSE,
        help="股票池 CSV（至少包含 ticker/name）",
    )
    parser.add_argument(
        "--dcf-data-dir",
        type=Path,
        default=DEFAULT_DCF_DATA_DIR,
        help="DCF 数据目录（companies.json / snapshots / valuations）",
    )
    parser.add_argument(
        "--seed-data-dir",
        type=Path,
        default=None,
        help="DCF seed 目录（默认与 --dcf-data-dir 相同）",
    )
    parser.add_argument(
        "--source-adapter",
        default="multi_source",
        choices=["yfinance", "alpha_vantage", "multi_source", "merged"],
        help="财报同步源",
    )
    parser.add_argument(
        "--operator",
        default="investor-method-lab:auto-seed",
        help="审计操作人标识",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="已存在公司时跳过（默认会刷新快照并重算估值）",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=DEFAULT_REPORT,
        help="结果报告输出",
    )
    return parser.parse_args()


def dcf_symbol_candidates(ticker: str) -> List[str]:
    raw = str(ticker or "").strip().upper()
    if not raw:
        return []
    candidates: List[str] = []
    if raw.endswith(".HK"):
        code = raw[:-3]
        if code.isdigit():
            candidates.extend([f"HK.{code.zfill(5)}", f"HK.{int(code)}"])
    elif raw.endswith(".SS"):
        code = raw[:-3]
        if code.isdigit():
            candidates.append(f"SH.{code}")
    elif raw.endswith(".SZ"):
        code = raw[:-3]
        if code.isdigit():
            candidates.append(f"SZ.{code}")
    elif raw.startswith(("US.", "SH.", "SZ.", "HK.")):
        prefix, _, tail = raw.partition(".")
        if prefix == "HK" and tail.isdigit():
            candidates.extend([f"HK.{tail.zfill(5)}", f"HK.{int(tail)}"])
        elif prefix == "US" and "." in tail:
            candidates.append(f"US.{tail.replace('.', '-')}")
            candidates.append(f"US.{tail}")
        elif tail:
            candidates.append(f"{prefix}.{tail}")
    else:
        if "." in raw:
            candidates.append(f"US.{raw.replace('.', '-')}")
        candidates.append(f"US.{raw}")

    dedup: List[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            dedup.append(item)
    return dedup


def resolve_dcf_symbol(ticker: str, existing_symbols: set[str]) -> str:
    candidates = dcf_symbol_candidates(ticker)
    if not candidates:
        raise ValueError(f"invalid ticker: {ticker}")
    for symbol in candidates:
        if symbol in existing_symbols:
            return symbol
    return candidates[0]


def pick_policy_id(symbol: str, policy_ids: set[str]) -> str:
    # Keep policy mapping simple and deterministic by market.
    if symbol.startswith("HK.") and "anchored-hk-platform-r09-g3" in policy_ids:
        return "anchored-hk-platform-r09-g3"
    if symbol.startswith(("SH.", "SZ.")) and "anchored-cn-us-stable-r085-g3" in policy_ids:
        return "anchored-cn-us-stable-r085-g3"
    if symbol.startswith("US.") and "anchored-us-quality-r09-g3" in policy_ids:
        return "anchored-us-quality-r09-g3"
    if "default-v1" in policy_ids:
        return "default-v1"
    return next(iter(policy_ids))


def build_company_profile(
    symbol: str,
    name_hint: str,
    policy_id: str,
) -> CompanyProfile:
    profile = fetch_company_profile_from_yfinance(symbol)
    if not profile:
        raise RuntimeError(f"{symbol}: yfinance company profile missing shares")

    currency = str(profile.get("currency") or "USD").upper()
    fx_rate = 1.0
    if symbol.startswith("HK."):
        # Keep aligned with existing DCF HK company defaults in current data store.
        fx_rate = 1.08
    elif symbol.startswith(("SH.", "SZ.")):
        fx_rate = 1.0

    return CompanyProfile(
        symbol=symbol,
        name=(str(profile.get("name") or "").strip() or name_hint or symbol),
        currency=currency,
        shares=float(profile["shares"]),
        fx_rate=fx_rate,
        active_policy_id=policy_id,
        growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
    )


def load_universe(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ensure_company(
    *,
    repo: JSONRepository,
    existing_companies: Dict[str, CompanyProfile],
    symbol: str,
    name_hint: str,
    policy_ids: set[str],
) -> tuple[CompanyProfile, str]:
    company = existing_companies.get(symbol)
    if company is not None:
        return company, "existing"

    policy_id = pick_policy_id(symbol, policy_ids)
    company = build_company_profile(symbol=symbol, name_hint=name_hint, policy_id=policy_id)
    repo.upsert_company(company)
    existing_companies[symbol] = company
    return company, "created"


def approve_and_calculate(
    *,
    service: DCFService,
    snapshot_id: str,
    symbol: str,
    operator: str,
) -> Any:
    reviewed = service.review_financials(
        snapshot_id=snapshot_id,
        decision="approve",
        comment="auto approve from investor-method-lab coverage seeding",
        operator=operator,
    )
    valuation = service.calculate(symbol=symbol, price=None, operator=operator)
    return reviewed, valuation


def seed_a_share_with_ths_fallback(
    *,
    service: DCFService,
    repo: JSONRepository,
    existing_companies: Dict[str, CompanyProfile],
    symbol: str,
    name_hint: str,
    policy_ids: set[str],
    operator: str,
) -> tuple[Any, Any]:
    # Reuse THS financial inputs from dcf service for A-share edge cases where
    # yfinance sync fails (e.g. net-cash fields missing / peak filter on source series).
    ths_snapshot, ths_shares, _ = service._load_financial_inputs_from_ths(symbol=symbol)  # noqa: SLF001
    company = existing_companies.get(symbol)
    if company is None:
        policy_id = pick_policy_id(symbol, policy_ids)
        company = CompanyProfile(
            symbol=symbol,
            name=name_hint or symbol,
            currency="CNY",
            shares=float(ths_shares),
            fx_rate=1.0,
            active_policy_id=policy_id,
            growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
        )
        repo.upsert_company(company)
        existing_companies[symbol] = company

    last_error: Exception | None = None
    for method in ("median", "mean"):
        try:
            manual_snapshot = service.update_financials(
                symbol=symbol,
                fiscal_year=ths_snapshot.fiscal_year,
                fcf_reported=ths_snapshot.fcf_reported,
                cash=ths_snapshot.cash,
                short_term_investments=ths_snapshot.short_term_investments,
                interest_bearing_debt=ths_snapshot.interest_bearing_debt,
                operator=operator,
                shares=float(ths_shares),
                name=company.name,
                currency=company.currency,
                fx_rate=company.fx_rate,
                growth_scenarios=company.growth_scenarios,
                active_policy_id=company.active_policy_id,
                normalization_method=method,
            )
            return approve_and_calculate(
                service=service,
                snapshot_id=manual_snapshot.snapshot_id,
                symbol=symbol,
                operator=operator,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"{symbol}: ths fallback failed without explicit error")


def main() -> None:
    args = parse_args()

    seed_dir = args.seed_data_dir or args.dcf_data_dir
    repo = JSONRepository(args.dcf_data_dir, seed_dir=seed_dir)
    service = DCFService(repo)

    existing_companies = {c.symbol: c for c in repo.list_companies()}
    policy_ids = {p.policy_id for p in repo.list_policies()}
    if not policy_ids:
        raise RuntimeError("No valuation policy found in DCF repository")

    universe = load_universe(args.universe_file)
    results: List[Dict[str, Any]] = []

    for row in universe:
        ticker = (row.get("ticker") or "").strip()
        name = (row.get("name") or "").strip()
        if not ticker:
            continue

        try:
            symbol = resolve_dcf_symbol(ticker, set(existing_companies.keys()))
        except Exception as exc:  # noqa: BLE001
            results.append(
                {"ticker": ticker, "status": "failed", "stage": "symbol_resolve", "error": str(exc)}
            )
            continue

        try:
            company, company_status = ensure_company(
                repo=repo,
                existing_companies=existing_companies,
                symbol=symbol,
                name_hint=name,
                policy_ids=policy_ids,
            )

            if args.skip_existing and company_status == "existing":
                results.append(
                    {
                        "ticker": ticker,
                        "symbol": symbol,
                        "status": "skipped_existing",
                        "company_status": company_status,
                    }
                )
                continue

            fallback_mode = None
            try:
                snapshot = service.sync_financials(
                    symbol=symbol,
                    source_adapter=args.source_adapter,
                    operator=args.operator,
                )
                reviewed, valuation = approve_and_calculate(
                    service=service,
                    snapshot_id=snapshot.snapshot_id,
                    symbol=symbol,
                    operator=args.operator,
                )
            except Exception as exc:  # noqa: BLE001
                if symbol.startswith(("SH.", "SZ.")):
                    reviewed, valuation = seed_a_share_with_ths_fallback(
                        service=service,
                        repo=repo,
                        existing_companies=existing_companies,
                        symbol=symbol,
                        name_hint=name,
                        policy_ids=policy_ids,
                        operator=args.operator,
                    )
                    fallback_mode = f"ths_manual:{exc.__class__.__name__}"
                else:
                    raise

            results.append(
                {
                    "ticker": ticker,
                    "symbol": symbol,
                    "status": "ok",
                    "company_status": company_status,
                    "snapshot_id": reviewed.snapshot_id,
                    "valuation_id": valuation.valuation_id,
                    "iv_base": valuation.iv_base,
                    "mos_base": valuation.mos_base,
                    "fallback_mode": fallback_mode,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "ticker": ticker,
                    "symbol": symbol,
                    "status": "failed",
                    "stage": "sync_or_valuation",
                    "error": str(exc),
                }
            )

    ok = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") == "failed"]
    skipped = [r for r in results if r.get("status") == "skipped_existing"]

    report = {
        "universe_file": str(args.universe_file),
        "dcf_data_dir": str(args.dcf_data_dir),
        "source_adapter": args.source_adapter,
        "operator": args.operator,
        "summary": {
            "total": len(results),
            "ok": len(ok),
            "failed": len(failed),
            "skipped_existing": len(skipped),
        },
        "results": results,
    }
    args.report_file.parent.mkdir(parents=True, exist_ok=True)
    args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"report: {args.report_file}")
    print(
        f"seed summary => total={len(results)} ok={len(ok)} "
        f"failed={len(failed)} skipped_existing={len(skipped)}"
    )
    if failed:
        print("failed symbols:")
        for item in failed:
            print(f"- {item.get('ticker')} -> {item.get('symbol')}: {item.get('error')}")


if __name__ == "__main__":
    main()
