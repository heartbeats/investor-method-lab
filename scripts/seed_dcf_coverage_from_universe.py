#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UNIVERSE = PROJECT_ROOT / "data" / "opportunities.universe_3markets.csv"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "dcf_coverage_seed_report.json"
DEFAULT_REAL_FILE = PROJECT_ROOT / "data" / "opportunities.real_3markets.csv"
DEFAULT_DCF_ROOT = Path((os.getenv("HIT_ZONE_PROJECT_DIR") or str(Path.home() / "projects" / "hit-zone")).strip()).expanduser()
DEFAULT_DCF_DATA_DIR = DEFAULT_DCF_ROOT / "data"
DEFAULT_SNAPSHOT_ROOT = Path.home() / "projects" / "stock-data-hub" / "data_lake" / "snapshots"

if str(DEFAULT_DCF_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_DCF_ROOT))

from dcf.models import CompanyProfile, GrowthScenarios, QuoteRecord  # noqa: E402
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
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="stock-data-hub 快照根目录（用于 shares/currency 本地兜底）",
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


def build_a_share_company_profile_from_ths(
    *,
    service: DCFService,
    symbol: str,
    name_hint: str,
    policy_id: str,
) -> CompanyProfile:
    try:
        import akshare as ak  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{symbol}: akshare unavailable for A-share company profile fallback") from exc

    code = symbol.split(".", maxsplit=1)[1]
    debt_df = ak.stock_financial_debt_ths(symbol=code, indicator="按报告期")
    if debt_df is None or getattr(debt_df, "empty", True):
        raise RuntimeError(f"{symbol}: THS debt rows missing for company profile fallback")

    debt_rows = service._select_annual_rows(debt_df.to_dict(orient="records"))  # noqa: SLF001
    if not debt_rows:
        raise RuntimeError(f"{symbol}: THS annual debt rows missing for company profile fallback")

    latest_debt = debt_rows[0]
    shares = service._parse_cn_number(latest_debt.get("实收资本（或股本）"))  # noqa: SLF001
    if shares is None or shares <= 0:
        raise RuntimeError(f"{symbol}: THS shares missing for company profile fallback")

    return CompanyProfile(
        symbol=symbol,
        name=name_hint or symbol,
        currency="CNY",
        shares=float(shares),
        fx_rate=1.0,
        active_policy_id=policy_id,
        growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
    )


def _load_jsonl_by_symbol(path: Path) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(payload, dict):
                continue
            symbol = str(payload.get("symbol") or "").strip().upper()
            if symbol:
                records[symbol] = payload
    return records


def _resolve_snapshot_dir(snapshot_root: Path) -> Path | None:
    if not snapshot_root.exists():
        return None
    dirs = sorted([item for item in snapshot_root.glob("dt=*") if item.is_dir()])
    if not dirs:
        return None
    return dirs[-1]


def load_snapshot_fundamentals(snapshot_root: Path) -> Dict[str, Dict[str, Any]]:
    if not snapshot_root.exists():
        return {}
    snapshot_dirs = sorted([item for item in snapshot_root.glob("dt=*") if item.is_dir()], reverse=True)
    if not snapshot_dirs:
        return {}
    merged: Dict[str, Dict[str, Any]] = {}
    for snapshot_dir in snapshot_dirs:
        payload = _load_jsonl_by_symbol(snapshot_dir / "fundamentals.jsonl")
        for symbol, record in payload.items():
            if symbol not in merged:
                merged[symbol] = record
    return merged


def build_company_profile_from_snapshot_fundamentals(
    *,
    symbol: str,
    name_hint: str,
    policy_id: str,
    snapshot_fundamentals: Dict[str, Dict[str, Any]] | None,
) -> CompanyProfile | None:
    if not snapshot_fundamentals:
        return None
    payload = snapshot_fundamentals.get(symbol) or {}
    if not isinstance(payload, dict) or not payload:
        return None
    shares = payload.get("shares_outstanding")
    if shares is None:
        shares = payload.get("weighted_average_shares")
    if shares is None:
        shares = payload.get("shares")
    try:
        shares_value = float(shares)
    except (TypeError, ValueError):
        return None
    if shares_value <= 0:
        return None
    currency = str(payload.get("currency") or "USD").upper()
    fx_rate = 1.0
    if symbol.startswith("HK."):
        fx_rate = 1.08
    elif symbol.startswith(("SH.", "SZ.")):
        fx_rate = 1.0
    company_name = str(payload.get("name") or name_hint or symbol).strip() or symbol
    return CompanyProfile(
        symbol=symbol,
        name=company_name,
        currency=currency,
        shares=shares_value,
        fx_rate=fx_rate,
        active_policy_id=policy_id,
        growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
    )


def build_company_profile(
    *,
    service: DCFService,
    symbol: str,
    name_hint: str,
    policy_id: str,
    snapshot_fundamentals: Dict[str, Dict[str, Any]] | None = None,
) -> tuple[CompanyProfile, str]:
    yfinance_error: Exception | None = None
    profile = None
    try:
        profile = fetch_company_profile_from_yfinance(symbol)
    except Exception as exc:  # noqa: BLE001
        yfinance_error = exc

    shares = None if not profile else profile.get("shares")
    if shares:
        currency = str(profile.get("currency") or "USD").upper()
        fx_rate = 1.0
        if symbol.startswith("HK."):
            fx_rate = 1.08
        elif symbol.startswith(("SH.", "SZ.")):
            fx_rate = 1.0

        return (
            CompanyProfile(
                symbol=symbol,
                name=(str(profile.get("name") or "").strip() or name_hint or symbol),
                currency=currency,
                shares=float(shares),
                fx_rate=fx_rate,
                active_policy_id=policy_id,
                growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
            ),
            "yfinance",
        )

    snapshot_company = build_company_profile_from_snapshot_fundamentals(
        symbol=symbol,
        name_hint=name_hint,
        policy_id=policy_id,
        snapshot_fundamentals=snapshot_fundamentals,
    )
    if snapshot_company is not None:
        return snapshot_company, "stock_data_snapshot_fundamentals"

    if symbol.startswith(("SH.", "SZ.")):
        placeholder_error: Exception | None = None
        try:
            return (
                build_a_share_company_profile_from_ths(
                    service=service,
                    symbol=symbol,
                    name_hint=name_hint,
                    policy_id=policy_id,
                ),
                "ths_company_profile",
            )
        except Exception as ths_exc:  # noqa: BLE001
            try:
                placeholder = build_runtime_shell_ready_company_profile(
                    service=service,
                    symbol=symbol,
                    name_hint=name_hint,
                    policy_id=policy_id,
                )
                if placeholder is not None:
                    return placeholder, "financial_template_placeholder"
            except Exception as placeholder_exc:  # noqa: BLE001
                placeholder_error = placeholder_exc
            detail_parts = []
            if yfinance_error is not None:
                detail_parts.append(f"yfinance={yfinance_error}")
            detail_parts.append(f"ths={ths_exc}")
            if placeholder_error is not None:
                detail_parts.append(f"placeholder={placeholder_error}")
            detail = " | ".join(detail_parts)
            raise RuntimeError(f"{symbol}: company profile fallback failed ({detail})") from ths_exc

    if yfinance_error is not None:
        raise RuntimeError(f"{symbol}: yfinance company profile unavailable ({yfinance_error})") from yfinance_error
    raise RuntimeError(f"{symbol}: yfinance company profile missing shares")


def build_runtime_shell_ready_company_profile(
    *,
    service: DCFService,
    symbol: str,
    name_hint: str,
    policy_id: str,
) -> CompanyProfile | None:
    if not symbol.startswith(("SH.", "SZ.")):
        return None
    profile = service._map_lookup_with_alias(service._hub_stock_profiles_index(), symbol) or {}  # noqa: SLF001
    row = {
        "name": (name_hint or profile.get("name_cn") or profile.get("name") or symbol),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
    }
    parameter_library = service._resolve_parameter_library(  # noqa: SLF001
        symbol=symbol,
        profile=profile,
        row=row,
        allow_on_demand_metrics=True,
    )
    family_id = str(parameter_library.get("financial_template_family_id") or "").strip()
    shell_model = str(parameter_library.get("financial_template_family_shell_model") or "").strip().lower()
    if not family_id or shell_model not in {"ri", "dcf"}:
        return None
    company_name = str(profile.get("name_cn") or profile.get("name") or name_hint or symbol).strip() or symbol
    return CompanyProfile(
        symbol=symbol,
        name=company_name,
        currency="CNY",
        shares=1.0,
        fx_rate=1.0,
        active_policy_id=policy_id,
        growth_scenarios=GrowthScenarios(bear=0.02, base=0.05, bull=0.08),
    )


def load_real_price_lookup(path: Path) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            try:
                fair_value = float(row.get("fair_value") or 0.0)
                price_to_fair_value = float(row.get("price_to_fair_value") or 0.0)
            except (TypeError, ValueError):
                continue
            close = fair_value * price_to_fair_value if fair_value > 0 and price_to_fair_value > 0 else None
            if close is None or close <= 0:
                continue
            note = str(row.get("note") or "")
            as_of_date = ""
            marker = "real-data@"
            if marker in note:
                tail = note.split(marker, 1)[1]
                as_of_date = tail[:10]
            rows[ticker] = {"close": close, "as_of_date": as_of_date or None}
    return rows


def seed_quote_from_real_lookup(
    *,
    repo: JSONRepository,
    symbol: str,
    ticker: str,
    real_price_lookup: Dict[str, Dict[str, Any]],
) -> str | None:
    existing_quotes = repo.get_quotes([symbol])
    if existing_quotes:
        return None
    payload = real_price_lookup.get(ticker)
    if not isinstance(payload, dict):
        return None
    try:
        close = float(payload.get("close"))
    except (TypeError, ValueError):
        return None
    if close <= 0:
        return None
    as_of_date = str(payload.get("as_of_date") or "2026-03-04").strip() or "2026-03-04"
    repo.upsert_quotes(
        [
            QuoteRecord(
                symbol=symbol,
                price=close,
                timestamp=f"{as_of_date}T15:00:00+08:00",
                source="investor_method_lab:real_opportunities_csv",
            )
        ]
    )
    return "real_opportunities_csv"


def load_universe(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ensure_company(
    *,
    repo: JSONRepository,
    service: DCFService,
    existing_companies: Dict[str, CompanyProfile],
    symbol: str,
    name_hint: str,
    policy_ids: set[str],
    snapshot_fundamentals: Dict[str, Dict[str, Any]] | None = None,
) -> tuple[CompanyProfile, str, str | None]:
    company = existing_companies.get(symbol)
    if company is not None:
        return company, "existing", None

    policy_id = pick_policy_id(symbol, policy_ids)
    company, seed_source = build_company_profile(
        service=service,
        symbol=symbol,
        name_hint=name_hint,
        policy_id=policy_id,
        snapshot_fundamentals=snapshot_fundamentals,
    )
    repo.upsert_company(company)
    existing_companies[symbol] = company
    return company, "created", seed_source


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
) -> tuple[Any, Any, str]:
    # Reuse THS financial inputs from dcf service for A-share edge cases where
    # yfinance sync fails (e.g. net-cash fields missing / peak filter on source series).
    ths_snapshot, ths_shares, ths_metrics = service._load_financial_inputs_from_ths(  # noqa: SLF001
        symbol=symbol,
        allow_peak_relaxed_fallback=True,
    )
    strategy_meta = (ths_metrics or {}).get("normalization_strategy") if isinstance(ths_metrics, dict) else {}
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

    strategy_candidates: list[tuple[str, int, bool, str]] = []
    seen_strategies: set[tuple[str, int, bool]] = set()

    def add_strategy(method: str, window_years: int, apply_peak_guard: bool, label: str) -> None:
        key = (str(method), int(window_years), bool(apply_peak_guard))
        if key in seen_strategies:
            return
        seen_strategies.add(key)
        strategy_candidates.append((key[0], key[1], key[2], label))

    primary_method = str((strategy_meta or {}).get("method") or "median")
    primary_window = int((strategy_meta or {}).get("window_years") or 3)
    primary_guard = bool((strategy_meta or {}).get("apply_peak_guard", True))
    add_strategy(primary_method, primary_window, primary_guard, "ths_primary")
    add_strategy("median", 3, True, "manual_strict_median")
    add_strategy("mean", 3, True, "manual_strict_mean")
    add_strategy("mean", 5, False, "manual_relaxed_mean5")

    last_error: Exception | None = None
    for method, window_years, apply_peak_guard, label in strategy_candidates:
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
                normalization_window_years=window_years,
                apply_peak_guard=apply_peak_guard,
            )
            reviewed, valuation = approve_and_calculate(
                service=service,
                snapshot_id=manual_snapshot.snapshot_id,
                symbol=symbol,
                operator=operator,
            )
            strategy_label = f"{label}:{method}:w{window_years}:{'guard' if apply_peak_guard else 'relaxed'}"
            return reviewed, valuation, strategy_label
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
    real_price_lookup = load_real_price_lookup(DEFAULT_REAL_FILE)
    snapshot_fundamentals = load_snapshot_fundamentals(args.snapshot_root)
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
            company, company_status, company_seed_source = ensure_company(
                repo=repo,
                service=service,
                existing_companies=existing_companies,
                symbol=symbol,
                name_hint=name,
                policy_ids=policy_ids,
                snapshot_fundamentals=snapshot_fundamentals,
            )
            quote_seed_source = seed_quote_from_real_lookup(
                repo=repo,
                symbol=symbol,
                ticker=ticker,
                real_price_lookup=real_price_lookup,
            )

            if args.skip_existing and company_status == "existing":
                results.append(
                    {
                        "ticker": ticker,
                        "symbol": symbol,
                        "status": "skipped_existing",
                        "company_status": company_status,
                        "company_seed_source": company_seed_source,
                        "quote_seed_source": quote_seed_source,
                    }
                )
                continue

            fallback_mode = None
            reviewed = None
            valuation: Any = None
            runtime_overview: Dict[str, Any] | None = None
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
                    try:
                        reviewed, valuation, ths_strategy_label = seed_a_share_with_ths_fallback(
                            service=service,
                            repo=repo,
                            existing_companies=existing_companies,
                            symbol=symbol,
                            name_hint=name,
                            policy_ids=policy_ids,
                            operator=args.operator,
                        )
                        fallback_mode = f"ths_manual:{ths_strategy_label}:{exc.__class__.__name__}"
                    except Exception as ths_exc:  # noqa: BLE001
                        runtime_overview = service.get_company_overview(symbol=symbol)
                        runtime_valuation = (
                            runtime_overview.get("latest_valuation") if isinstance(runtime_overview, dict) else None
                        )
                        if isinstance(runtime_valuation, dict) and runtime_valuation.get("iv_base"):
                            valuation = runtime_valuation
                            fallback_mode = (
                                f"runtime_shell:{exc.__class__.__name__}/{ths_exc.__class__.__name__}"
                            )
                        else:
                            raise ths_exc
                else:
                    raise

            latest_snapshot = runtime_overview.get("latest_snapshot") if isinstance(runtime_overview, dict) else {}
            latest_snapshot = latest_snapshot if isinstance(latest_snapshot, dict) else {}
            snapshot_id = (
                reviewed.snapshot_id if reviewed is not None else str(latest_snapshot.get("snapshot_id") or "") or None
            )
            valuation_id = (
                valuation.valuation_id if hasattr(valuation, "valuation_id") else str((valuation or {}).get("valuation_id") or "") or None
            )
            iv_base = valuation.iv_base if hasattr(valuation, "iv_base") else (valuation or {}).get("iv_base")
            mos_base = valuation.mos_base if hasattr(valuation, "mos_base") else (valuation or {}).get("mos_base")

            results.append(
                {
                    "ticker": ticker,
                    "symbol": symbol,
                    "status": "ok",
                    "company_status": company_status,
                    "company_seed_source": company_seed_source,
                    "quote_seed_source": quote_seed_source,
                    "snapshot_id": snapshot_id,
                    "valuation_id": valuation_id,
                    "iv_base": iv_base,
                    "mos_base": mos_base,
                    "fallback_mode": fallback_mode,
                }
            )
        except Exception as exc:  # noqa: BLE001
            failed_item = {
                "ticker": ticker,
                "symbol": symbol,
                "status": "failed",
                "stage": "sync_or_valuation",
                "error": str(exc),
            }
            error_details = getattr(exc, "details", None)
            if isinstance(error_details, dict) and error_details:
                failed_item["error_details"] = error_details
            results.append(failed_item)

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
