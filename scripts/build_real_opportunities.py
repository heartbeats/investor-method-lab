#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import csv
import json
import math
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from urllib.parse import urlparse

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DCF_LINK_SCRIPT = Path(
    "/home/afu/.codex/skills/dcf-valuation-link/scripts/dcf_valuation_link.py"
)
DEFAULT_DCF_COMPANIES_FILE = Path("/home/afu/codex-project/data/companies.json")

YF_TICKER_MAP = {
    "BRK.B": "BRK-B",
    "BF.B": "BF-B",
}

LOCAL_SNAPSHOT_CONTEXT: Dict[str, Any] = {
    "enabled": False,
    "snapshot_date": "",
    "snapshot_dir": "",
    "quotes": {},
    "fundamentals": {},
    "external_valuations": {},
    "price_history": {},
    "financial_statements": {},
}


def normalize_yf_ticker(ticker: str) -> str:
    raw = str(ticker or "").strip().upper()
    if raw.endswith(".HK"):
        code = raw[:-3]
        if code.isdigit():
            # Yahoo HK ticker usually uses 4-digit code (e.g. 0700.HK, 0005.HK, 9988.HK).
            return f"{int(code):04d}.HK"
    return raw


def normalize_internal_symbol_for_ticker(ticker: str) -> str:
    raw = str(ticker or "").strip().upper()
    if not raw:
        return ""
    if raw.startswith(("SH.", "SZ.", "HK.", "US.")):
        return raw
    if raw.endswith(".SS") and raw[:-3].isdigit():
        return f"SH.{raw[:-3]}"
    if raw.endswith(".SZ") and raw[:-3].isdigit():
        return f"SZ.{raw[:-3]}"
    if raw.endswith(".HK"):
        code = raw[:-3]
        if code.isdigit():
            return f"HK.{int(code):05d}"
    us_tail = raw.replace(".", "-")
    return f"US.{us_tail}"


def snapshot_symbol_aliases(ticker: str) -> List[str]:
    aliases: List[str] = []
    internal = normalize_internal_symbol_for_ticker(ticker)
    if internal:
        aliases.append(internal)
    raw = str(ticker or "").strip().upper()
    if raw:
        aliases.append(raw)
    if internal.startswith("US."):
        aliases.append(internal.split(".", 1)[1])
    dedup: List[str] = []
    seen = set()
    for item in aliases:
        normalized = str(item or "").strip().upper()
        if normalized and normalized not in seen:
            dedup.append(normalized)
            seen.add(normalized)
    return dedup


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
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            symbol = str(payload.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            records[symbol] = payload
    return records


def _resolve_snapshot_dir(snapshot_root: Path, snapshot_date: str | None) -> Path | None:
    if not snapshot_root.exists():
        return None
    if snapshot_date:
        direct = snapshot_root / f"dt={snapshot_date}"
        if direct.exists():
            return direct
    dirs = sorted([p for p in snapshot_root.glob("dt=*") if p.is_dir()])
    if not dirs:
        return None
    return dirs[-1]


def _snapshot_meta_summary(context: Dict[str, Any]) -> Dict[str, Any]:
    quotes = context.get("quotes")
    fundamentals = context.get("fundamentals")
    external = context.get("external_valuations")
    price_history = context.get("price_history")
    financial_statements = context.get("financial_statements")
    return {
        "enabled": bool(context.get("enabled")),
        "snapshot_date": str(context.get("snapshot_date") or ""),
        "snapshot_dir": str(context.get("snapshot_dir") or ""),
        "quotes_count": len(quotes) if isinstance(quotes, dict) else 0,
        "fundamentals_count": len(fundamentals) if isinstance(fundamentals, dict) else 0,
        "external_valuations_count": len(external) if isinstance(external, dict) else 0,
        "price_history_count": len(price_history) if isinstance(price_history, dict) else 0,
        "financial_statements_count": len(financial_statements) if isinstance(financial_statements, dict) else 0,
        "reason": str(context.get("reason") or ""),
    }


def configure_local_snapshot_context(*, snapshot_root: Path, snapshot_date: str | None, enabled: bool) -> Dict[str, Any]:
    global LOCAL_SNAPSHOT_CONTEXT
    if not enabled:
        LOCAL_SNAPSHOT_CONTEXT = {
            "enabled": False,
            "snapshot_date": "",
            "snapshot_dir": "",
            "quotes": {},
            "fundamentals": {},
            "external_valuations": {},
            "price_history": {},
            "financial_statements": {},
        }
        return _snapshot_meta_summary(LOCAL_SNAPSHOT_CONTEXT)

    snapshot_dir = _resolve_snapshot_dir(snapshot_root, snapshot_date)
    if snapshot_dir is None:
        LOCAL_SNAPSHOT_CONTEXT = {
            "enabled": False,
            "snapshot_date": "",
            "snapshot_dir": str(snapshot_root),
            "quotes": {},
            "fundamentals": {},
            "external_valuations": {},
            "price_history": {},
            "financial_statements": {},
            "reason": "snapshot_dir_not_found",
        }
        return _snapshot_meta_summary(LOCAL_SNAPSHOT_CONTEXT)

    quotes = _load_jsonl_by_symbol(snapshot_dir / "quotes.jsonl")
    fundamentals = _load_jsonl_by_symbol(snapshot_dir / "fundamentals.jsonl")
    external_valuations = _load_jsonl_by_symbol(snapshot_dir / "external_valuations.jsonl")
    price_history = _load_jsonl_by_symbol(snapshot_dir / "price_history.jsonl")
    financial_statements = _load_jsonl_by_symbol(snapshot_dir / "financial_statements.jsonl")
    snapshot_dt = snapshot_dir.name.replace("dt=", "")
    LOCAL_SNAPSHOT_CONTEXT = {
        "enabled": True,
        "snapshot_date": snapshot_dt,
        "snapshot_dir": str(snapshot_dir),
        "quotes": quotes,
        "fundamentals": fundamentals,
        "external_valuations": external_valuations,
        "price_history": price_history,
        "financial_statements": financial_statements,
    }
    return _snapshot_meta_summary(LOCAL_SNAPSHOT_CONTEXT)


def get_snapshot_record(domain: str, ticker: str) -> Dict[str, Any] | None:
    if not LOCAL_SNAPSHOT_CONTEXT.get("enabled"):
        return None
    records = LOCAL_SNAPSHOT_CONTEXT.get(domain)
    if not isinstance(records, dict) or not records:
        return None
    for alias in snapshot_symbol_aliases(ticker):
        payload = records.get(alias)
        if isinstance(payload, dict):
            return payload
    return None


def _stock_data_hub_url() -> str | None:
    raw = (os.getenv("IML_STOCK_DATA_HUB_URL") or "").strip().rstrip("/")
    return raw or None


def _hub_get_json(path: str, query: Dict[str, str], timeout_sec: float) -> Dict[str, Any] | None:
    base_url = _stock_data_hub_url()
    if not base_url:
        return None
    qs = urllib_parse.urlencode(query)
    req = urllib_request.Request(f"{base_url}/{path}?{qs}", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=max(1.0, float(timeout_sec))) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _hub_post_json(path: str, payload: Dict[str, Any], timeout_sec: float) -> Dict[str, Any] | None:
    base_url = _stock_data_hub_url()
    if not base_url:
        return None
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(
        f"{base_url}/{path}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=max(1.0, float(timeout_sec))) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _skip_hub_online() -> bool:
    return str(os.getenv("IML_SKIP_HUB_ONLINE", "0")).strip().lower() in {"1", "true", "yes", "on"}


def fetch_quote_from_stock_data_hub(ticker: str, timeout_sec: float = 6.0) -> Dict[str, Any] | None:
    if _skip_hub_online():
        return None
    symbol = str(ticker or "").strip()
    if not symbol:
        return None

    payload = _hub_get_json(
        path="v1/quote",
        query={
            "symbol": symbol,
            "mode": "non_realtime",
            "refresh": "false",
        },
        timeout_sec=timeout_sec,
    )
    if not payload:
        return None

    price = _safe_float(payload.get("price"))
    if price is None or price <= 0:
        return None

    as_of_raw = str(payload.get("as_of") or "").strip()
    as_of_date = as_of_raw[:10] if len(as_of_raw) >= 10 else datetime.now(timezone.utc).date().isoformat()
    return {
        "price": float(price),
        "as_of_date": as_of_date,
        "provider": str(payload.get("provider") or "stock_data_hub"),
        "quality_flag": str(payload.get("quality_flag") or ""),
    }


def fetch_external_valuation_from_stock_data_hub(
    ticker: str,
    timeout_sec: float = 6.0,
) -> Dict[str, Any] | None:
    if _skip_hub_online():
        return None
    symbol = str(ticker or "").strip()
    if not symbol:
        return None
    payload = _hub_get_json(
        path="v1/external-valuation",
        query={
            "symbol": symbol,
            "mode": "non_realtime",
            "refresh": "false",
        },
        timeout_sec=timeout_sec,
    )
    if not payload:
        return None
    mean = _safe_float(payload.get("target_mean_price"))
    median = _safe_float(payload.get("target_median_price"))
    high = _safe_float(payload.get("target_high_price"))
    low = _safe_float(payload.get("target_low_price"))
    if mean is None and median is None and high is None and low is None:
        return None
    return {
        "provider": str(payload.get("provider") or "stock_data_hub"),
        "target_mean_price": mean,
        "target_median_price": median,
        "target_high_price": high,
        "target_low_price": low,
        "analyst_count": _safe_float(payload.get("analyst_count")),
        "recommendation_mean": _first_valid(
            payload.get("recommendation_mean"),
            payload.get("target_rating_mean"),
        ),
    }


def fetch_fundamental_from_stock_data_hub(
    ticker: str,
    timeout_sec: float = 6.0,
) -> Dict[str, Any] | None:
    if _skip_hub_online():
        return None
    symbol = str(ticker or "").strip()
    if not symbol:
        return None
    payload = _hub_get_json(
        path="v1/fundamental",
        query={
            "symbol": symbol,
            "mode": "non_realtime",
            "refresh": "false",
        },
        timeout_sec=timeout_sec,
    )
    if not payload:
        return None
    values = {
        "provider": str(payload.get("provider") or "stock_data_hub"),
        "return_on_equity": _safe_float(payload.get("return_on_equity")),
        "gross_margins": _safe_float(payload.get("gross_margin")),
        "operating_margins": _safe_float(payload.get("operating_margin")),
        "revenue_growth": _safe_float(payload.get("revenue_growth")),
        "earnings_growth": _safe_float(payload.get("earnings_growth")),
        "debt_to_equity": _safe_float(payload.get("debt_to_equity")),
        "analyst_count": _safe_float(payload.get("analyst_count")),
    }
    if all(values.get(k) is None for k in values if k != "provider"):
        return None
    return values


def fetch_price_history_from_stock_data_hub(
    ticker: str,
    period: str,
    interval: str = "1d",
    timeout_sec: float = 8.0,
) -> pd.Series:
    symbol = str(ticker or "").strip()
    if not symbol:
        return pd.Series(dtype=float)
    snapshot_history = get_snapshot_record("price_history", symbol)
    if isinstance(snapshot_history, dict):
        candles = snapshot_history.get("candles")
        if isinstance(candles, list) and candles:
            pairs: list[tuple[str, float]] = []
            for item in candles:
                if not isinstance(item, dict):
                    continue
                ts = str(item.get("ts") or "").strip()
                close = _safe_float(item.get("close"))
                if not ts or close is None:
                    continue
                pairs.append((ts, float(close)))
            if pairs:
                pairs.sort(key=lambda x: x[0])
                idx = pd.to_datetime([item[0] for item in pairs], errors="coerce", utc=True)
                vals = [item[1] for item in pairs]
                series = pd.Series(vals, index=idx, dtype=float).dropna()
                if not series.empty:
                    return series
    skip_hub_history = str(os.getenv("IML_SKIP_HUB_PRICE_HISTORY", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if skip_hub_history or _skip_hub_online():
        return pd.Series(dtype=float)
    payload = _hub_get_json(
        path="v1/price-history",
        query={
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "mode": "non_realtime",
            "refresh": "false",
        },
        timeout_sec=timeout_sec,
    )
    if not payload:
        return pd.Series(dtype=float)
    candles = payload.get("candles")
    if not isinstance(candles, list) or not candles:
        return pd.Series(dtype=float)
    pairs: list[tuple[str, float]] = []
    for item in candles:
        if not isinstance(item, dict):
            continue
        ts = str(item.get("ts") or "").strip()
        close = _safe_float(item.get("close"))
        if not ts or close is None:
            continue
        pairs.append((ts, float(close)))
    if not pairs:
        return pd.Series(dtype=float)
    pairs.sort(key=lambda x: x[0])
    idx = pd.to_datetime([item[0] for item in pairs], errors="coerce", utc=True)
    vals = [item[1] for item in pairs]
    series = pd.Series(vals, index=idx, dtype=float).dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series


def _first_valid(*candidates: Any) -> float | None:
    for value in candidates:
        parsed = _safe_float(value)
        if parsed is not None:
            return parsed
    return None


def _normalize_analyst_count(value: float | None) -> float | None:
    if value is None:
        return None
    if value < 0:
        return None
    return value


def _target_from_sources(
    yf_target: float | None,
    hub_external: Dict[str, Any] | None,
) -> tuple[float | None, str]:
    if yf_target is not None and yf_target > 0:
        return yf_target, "target_mean_price"
    if hub_external:
        mean = _safe_float(hub_external.get("target_mean_price"))
        if mean is not None and mean > 0:
            return mean, "target_mean_price"
    return None, "close_fallback"


def _target_detail(yf_target: float | None, hub_external: Dict[str, Any] | None) -> str:
    if yf_target is not None and yf_target > 0:
        return "yahoo_target_mean_price"
    if hub_external and _safe_float(hub_external.get("target_mean_price")) is not None:
        provider = str(hub_external.get("provider") or "stock_data_hub")
        return f"target_mean_price(stock_data_hub:{provider})"
    return "close_fallback"


def _build_row_name(item: Dict[str, str], info: Dict[str, Any], ticker: str) -> str:
    return (item.get("name") or info.get("longName") or ticker).strip()


def _build_row_sector(item: Dict[str, str], info: Dict[str, Any]) -> str:
    return (info.get("sector") or item.get("sector") or "Unknown").strip()


def _calc_quality_fields(
    info: Dict[str, Any],
    hub_fundamental: Dict[str, Any] | None,
    hub_external: Dict[str, Any] | None,
) -> Dict[str, float | None]:
    return {
        "return_on_equity": _first_valid(info.get("returnOnEquity"), (hub_fundamental or {}).get("return_on_equity")),
        "gross_margins": _first_valid(info.get("grossMargins"), (hub_fundamental or {}).get("gross_margins")),
        "operating_margins": _first_valid(
            info.get("operatingMargins"),
            (hub_fundamental or {}).get("operating_margins"),
        ),
        "revenue_growth": _first_valid(info.get("revenueGrowth"), (hub_fundamental or {}).get("revenue_growth")),
        "earnings_growth": _first_valid(info.get("earningsGrowth"), (hub_fundamental or {}).get("earnings_growth")),
        "earnings_quarterly_growth": _safe_float(info.get("earningsQuarterlyGrowth")),
        "debt_to_equity": _first_valid(info.get("debtToEquity"), (hub_fundamental or {}).get("debt_to_equity")),
        "beta": _safe_float(info.get("beta")),
        "analyst_count": _normalize_analyst_count(
            _first_valid(
                info.get("numberOfAnalystOpinions"),
                (hub_fundamental or {}).get("analyst_count"),
                (hub_external or {}).get("analyst_count"),
            )
        ),
        "recommendation_mean": _first_valid(
            info.get("recommendationMean"),
            (hub_external or {}).get("recommendation_mean"),
        ),
    }


def _build_valuation_detail(
    valuation_source: str,
    yf_target: float | None,
    hub_external: Dict[str, Any] | None,
    hub_quote: Dict[str, Any] | None,
) -> str:
    if valuation_source == "target_mean_price":
        return _target_detail(yf_target, hub_external)
    if hub_quote is not None:
        provider = str(hub_quote.get("provider") or "stock_data_hub")
        return f"close_fallback(stock_data_hub:{provider})"
    return "close_fallback"


@dataclass
class DCFValuation:
    symbol: str
    iv_base: float | None
    consensus_fair_value: float | None
    price: float | None
    mos_base: float | None
    status: str | None
    pulled_at: str | None
    quality_gate_status: str | None = None
    quality_gate_score: float | None = None
    quality_gate_issues: list[str] | None = None
    comps_crosscheck_status: str | None = None
    comps_crosscheck_deviation: float | None = None
    comps_crosscheck_source: str | None = None


@dataclass
class RawMarketRow:
    ticker: str
    yf_ticker: str
    name: str
    sector: str
    as_of_date: str
    close: float
    fair_value: float
    target_mean_price: float | None
    return_on_equity: float | None
    gross_margins: float | None
    operating_margins: float | None
    revenue_growth: float | None
    earnings_growth: float | None
    earnings_quarterly_growth: float | None
    debt_to_equity: float | None
    beta: float | None
    analyst_count: float | None
    recommendation_mean: float | None
    ret_3m: float | None
    ret_6m: float | None
    ret_12m: float | None
    dist_to_sma200: float | None
    vol_1y: float | None
    max_drawdown_1y: float | None
    note: str
    valuation_source: str = "target_mean_price"
    valuation_source_detail: str = ""
    dcf_symbol: str | None = None
    dcf_iv_base: float | None = None
    dcf_mos_base: float | None = None
    dcf_price: float | None = None
    dcf_status: str | None = None
    dcf_pulled_at: str | None = None
    dcf_quality_gate_status: str | None = None
    dcf_quality_gate_score: float | None = None
    dcf_quality_gate_issues: str = ""
    dcf_comps_crosscheck_status: str | None = None
    dcf_comps_deviation_vs_median: float | None = None
    dcf_comps_source: str | None = None
    dcf_quality_penalty_multiplier: float = 1.0
    base_note: str = ""
    data_lineage: str = ""


def _to_hub_external_payload(snapshot_external: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provider": str(snapshot_external.get("provider") or "stock_data_hub_snapshot"),
        "target_mean_price": _safe_float(snapshot_external.get("target_mean_price")),
        "target_median_price": _safe_float(snapshot_external.get("target_median_price")),
        "target_high_price": _safe_float(snapshot_external.get("target_high_price")),
        "target_low_price": _safe_float(snapshot_external.get("target_low_price")),
        "analyst_count": _safe_float(snapshot_external.get("analyst_count")),
        "recommendation_mean": _first_valid(
            snapshot_external.get("recommendation_mean"),
            snapshot_external.get("target_rating_mean"),
        ),
    }


def _to_hub_fundamental_payload(snapshot_fundamental: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provider": str(snapshot_fundamental.get("provider") or "stock_data_hub_snapshot"),
        "return_on_equity": _safe_float(snapshot_fundamental.get("return_on_equity")),
        "gross_margins": _safe_float(snapshot_fundamental.get("gross_margin")),
        "operating_margins": _safe_float(snapshot_fundamental.get("operating_margin")),
        "revenue_growth": _safe_float(snapshot_fundamental.get("revenue_growth")),
        "earnings_growth": _safe_float(snapshot_fundamental.get("earnings_growth")),
        "debt_to_equity": _safe_float(snapshot_fundamental.get("debt_to_equity")),
        "analyst_count": _safe_float(snapshot_fundamental.get("analyst_count")),
    }


def enrich_cached_row_with_backfill(row: RawMarketRow) -> None:
    snapshot_external = get_snapshot_record("external_valuations", row.ticker)
    snapshot_fundamental = get_snapshot_record("fundamentals", row.ticker)

    need_external = (
        row.target_mean_price is None
        or row.target_mean_price <= 0
        or row.analyst_count is None
        or row.recommendation_mean is None
    )
    hub_external: Dict[str, Any] | None = None
    if need_external:
        if isinstance(snapshot_external, dict):
            hub_external = _to_hub_external_payload(snapshot_external)
        if hub_external is None:
            hub_external = fetch_external_valuation_from_stock_data_hub(ticker=row.ticker, timeout_sec=6.0)
        if isinstance(hub_external, dict):
            target_mean = _safe_float(hub_external.get("target_mean_price"))
            if (row.target_mean_price is None or row.target_mean_price <= 0) and target_mean is not None and target_mean > 0:
                row.target_mean_price = target_mean
                if row.valuation_source == "close_fallback":
                    row.fair_value = target_mean
                    row.valuation_source = "target_mean_price"
                    provider = str(hub_external.get("provider") or "stock_data_hub")
                    row.valuation_source_detail = f"target_mean_price(stock_data_hub:{provider})"
            if row.analyst_count is None:
                analyst_count = _normalize_analyst_count(_safe_float(hub_external.get("analyst_count")))
                if analyst_count is not None:
                    row.analyst_count = analyst_count
            if row.recommendation_mean is None:
                recommendation_mean = _safe_float(hub_external.get("recommendation_mean"))
                if recommendation_mean is not None:
                    row.recommendation_mean = recommendation_mean

    need_fundamental = (
        row.return_on_equity is None
        or row.gross_margins is None
        or row.operating_margins is None
        or row.revenue_growth is None
        or row.earnings_growth is None
        or row.debt_to_equity is None
    )
    if need_fundamental:
        hub_fundamental: Dict[str, Any] | None = None
        if isinstance(snapshot_fundamental, dict):
            hub_fundamental = _to_hub_fundamental_payload(snapshot_fundamental)
        if hub_fundamental is None:
            hub_fundamental = fetch_fundamental_from_stock_data_hub(ticker=row.ticker, timeout_sec=6.0)
        if isinstance(hub_fundamental, dict):
            row.return_on_equity = _first_valid(row.return_on_equity, hub_fundamental.get("return_on_equity"))
            row.gross_margins = _first_valid(row.gross_margins, hub_fundamental.get("gross_margins"))
            row.operating_margins = _first_valid(row.operating_margins, hub_fundamental.get("operating_margins"))
            row.revenue_growth = _first_valid(row.revenue_growth, hub_fundamental.get("revenue_growth"))
            row.earnings_growth = _first_valid(row.earnings_growth, hub_fundamental.get("earnings_growth"))
            row.debt_to_equity = _first_valid(row.debt_to_equity, hub_fundamental.get("debt_to_equity"))

    row.note = _build_note(
        base_note=row.base_note,
        as_of_date=row.as_of_date,
        close=row.close,
        target_mean=row.target_mean_price,
        fair_value=row.fair_value,
        valuation_source=row.valuation_source,
        dcf_symbol=row.dcf_symbol,
        dcf_iv_base=row.dcf_iv_base,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建实时数据版机会池输入（stock-data-hub）")
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.universe_core_3markets.csv",
        help="股票池输入文件（至少需要 ticker；推荐 opportunities.universe_core_3markets.csv）",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real.csv",
        help="实时机会池输出 CSV",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=PROJECT_ROOT / "docs" / "opportunities_real_data_meta.json",
        help="实时数据元信息输出 JSON",
    )
    parser.add_argument(
        "--history-period",
        default="2y",
        help="行情历史回看区间（默认 2y）",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "cache" / "stock_data_hub",
        help="API 缓存目录（默认 data/cache/stock_data_hub）",
    )
    parser.add_argument(
        "--cache-ttl-hours",
        type=int,
        default=24,
        help="缓存有效期（小时，默认 24）",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存，强制实时拉取",
    )
    parser.add_argument(
        "--disable-dcf",
        action="store_true",
        help="禁用 DCF 估值覆盖（默认启用）",
    )
    parser.add_argument(
        "--dcf-link-script",
        type=Path,
        default=DEFAULT_DCF_LINK_SCRIPT,
        help="dcf_valuation_link.py 脚本路径",
    )
    parser.add_argument(
        "--dcf-companies-file",
        type=Path,
        default=DEFAULT_DCF_COMPANIES_FILE,
        help="DCF 公司清单路径（用于加速命中，文件不存在时自动降级）",
    )
    parser.add_argument(
        "--dcf-base-url",
        default="http://127.0.0.1:8000",
        help="DCF API 地址（默认 http://127.0.0.1:8000）",
    )
    parser.add_argument(
        "--dcf-timeout",
        type=float,
        default=15.0,
        help="DCF 拉取超时时间（秒）",
    )
    parser.add_argument(
        "--dcf-strict",
        action="store_true",
        help="DCF 拉取失败时直接报错（默认自动回退）",
    )
    parser.add_argument(
        "--per-ticker-timeout-seconds",
        type=float,
        default=25.0,
        help="单只股票拉取超时（秒，默认 25）",
    )
    parser.add_argument(
        "--per-ticker-retries",
        type=int,
        default=1,
        help="单只股票拉取失败重试次数（默认 1）",
    )
    parser.add_argument(
        "--per-ticker-retry-timeout-multiplier",
        type=float,
        default=1.5,
        help="每次重试的超时放大倍数（默认 1.5）",
    )
    parser.add_argument(
        "--per-ticker-retry-backoff-seconds",
        type=float,
        default=0.25,
        help="重试退避基准秒数（默认 0.25）",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="允许部分成功：失败 ticker 跳过并继续产出（默认关闭）",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path("/home/afu/projects/stock-data-hub/data_lake/snapshots"),
        help="本地股票快照目录根路径（dt=YYYY-MM-DD 子目录）",
    )
    parser.add_argument(
        "--snapshot-date",
        default="",
        help="指定快照日期（YYYY-MM-DD）；默认自动选择最新快照",
    )
    parser.add_argument(
        "--disable-local-snapshot",
        action="store_true",
        help="禁用本地快照读取（默认启用）",
    )
    return parser.parse_args()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _calc_return(closes: pd.Series, lookback: int) -> float | None:
    if len(closes) <= lookback:
        return None
    base = float(closes.iloc[-lookback - 1])
    now = float(closes.iloc[-1])
    if base == 0:
        return None
    return now / base - 1.0


def _calc_max_drawdown(closes: pd.Series) -> float | None:
    if closes.empty:
        return None
    peak = closes.cummax()
    drawdown = closes / peak - 1.0
    value = float(drawdown.min())
    return abs(value)


def load_universe(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def dcf_symbol_candidates(ticker: str) -> List[str]:
    raw = str(ticker or "").strip().upper()
    if not raw:
        return []

    candidates: List[str] = []

    if raw.startswith(("US.", "SH.", "SZ.", "HK.")):
        prefix, _, tail = raw.partition(".")
        if prefix == "HK" and tail.isdigit():
            candidates.append(f"HK.{tail.zfill(5)}")
            compact = str(int(tail))
            candidates.append(f"HK.{compact}")
        elif tail:
            candidates.append(f"{prefix}.{tail}")
    elif raw.endswith(".HK"):
        code = raw[:-3]
        if code.isdigit():
            candidates.append(f"HK.{code.zfill(5)}")
            candidates.append(f"HK.{int(code)}")
    elif raw.endswith(".SS"):
        code = raw[:-3]
        if code.isdigit():
            candidates.append(f"SH.{code}")
    elif raw.endswith(".SZ"):
        code = raw[:-3]
        if code.isdigit():
            candidates.append(f"SZ.{code}")
    else:
        if "." in raw:
            candidates.append(f"US.{raw.replace('.', '-')}")
        candidates.append(f"US.{raw}")

    dedup: List[str] = []
    seen = set()
    for item in candidates:
        symbol = item.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        dedup.append(symbol)
    return dedup


def resolve_dcf_symbol(ticker: str, available_symbols: set[str] | None = None) -> str | None:
    candidates = dcf_symbol_candidates(ticker)
    if not candidates:
        return None
    if available_symbols is None:
        return candidates[0]
    for symbol in candidates:
        if symbol in available_symbols:
            return symbol
    return None


def _load_dcf_available_symbols(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return None
        result = {
            str(item.get("symbol", "")).strip().upper()
            for item in payload
            if isinstance(item, dict) and item.get("symbol")
        }
        return result or None
    except Exception:  # noqa: BLE001
        return None


def _is_loopback_base_url(base_url: str) -> bool:
    host = (urlparse(base_url).hostname or "").strip().lower()
    return host in {"localhost", "::1"} or host.startswith("127.")


def _build_dcf_subprocess_env(dcf_base_url: str) -> Dict[str, str] | None:
    if not _is_loopback_base_url(dcf_base_url):
        return None

    env = os.environ.copy()
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        env.pop(key, None)

    direct_hosts = ["127.0.0.1", "localhost", "::1"]
    existing_no_proxy = env.get("NO_PROXY", "")
    existing_no_proxy_lower = env.get("no_proxy", "")
    merged_hosts = [item for item in existing_no_proxy.split(",") if item.strip()]
    merged_hosts += [item for item in existing_no_proxy_lower.split(",") if item.strip()]
    for host in direct_hosts:
        if host not in merged_hosts:
            merged_hosts.append(host)
    merged_value = ",".join(merged_hosts)
    env["NO_PROXY"] = merged_value
    env["no_proxy"] = merged_value
    return env


def _run_dcf_link_with_env(args: List[str], dcf_base_url: str) -> Dict[str, Any]:
    env = _build_dcf_subprocess_env(dcf_base_url)
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or "unknown error"
        raise RuntimeError(detail)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("dcf link returned invalid JSON payload") from exc


def _parse_dcf_company_payload(payload: Dict[str, Any]) -> DCFValuation | None:
    symbol = str(payload.get("symbol", "")).strip().upper()
    valuation = payload.get("valuation") if isinstance(payload, dict) else {}
    external_validation = (
        payload.get("external_validation") if isinstance(payload, dict) else {}
    )
    consensus = (
        external_validation.get("consensus")
        if isinstance(external_validation, dict)
        else {}
    )
    if not symbol or not isinstance(valuation, dict):
        return None
    iv_base = _safe_float(valuation.get("iv_base"))
    consensus_fair_value = (
        _safe_float(consensus.get("fair_value_median")) if isinstance(consensus, dict) else None
    )
    quality_gate = valuation.get("valuation_quality_gate")
    if not isinstance(quality_gate, dict):
        quality_gate = {}
    comps_crosscheck = valuation.get("comps_crosscheck")
    if not isinstance(comps_crosscheck, dict):
        comps_crosscheck = {}

    quality_gate_issues_raw = quality_gate.get("issues")
    quality_gate_issues: list[str] = []
    if isinstance(quality_gate_issues_raw, list):
        quality_gate_issues = [str(item).strip() for item in quality_gate_issues_raw if str(item).strip()]

    return DCFValuation(
        symbol=symbol,
        iv_base=iv_base,
        consensus_fair_value=consensus_fair_value,
        price=_safe_float(valuation.get("price")),
        mos_base=_safe_float(valuation.get("mos_base")),
        status=str(valuation.get("status", "")).strip() or None,
        pulled_at=str(payload.get("pulled_at", "")).strip() or None,
        quality_gate_status=str(quality_gate.get("status", "")).strip() or None,
        quality_gate_score=_safe_float(quality_gate.get("score")),
        quality_gate_issues=quality_gate_issues,
        comps_crosscheck_status=str(comps_crosscheck.get("status", "")).strip() or None,
        comps_crosscheck_deviation=_safe_float(comps_crosscheck.get("deviation_vs_median")),
        comps_crosscheck_source=str(comps_crosscheck.get("source", "")).strip() or None,
    )


def _dcf_quality_penalty_multiplier(
    *,
    quality_gate_status: str | None,
    comps_crosscheck_status: str | None,
) -> float:
    def _factor(name: str, default: float, min_value: float = 0.5, max_value: float = 1.0) -> float:
        raw = str(os.getenv(name, str(default))).strip()
        try:
            parsed = float(raw)
        except ValueError:
            parsed = default
        return max(min_value, min(parsed, max_value))

    review_factor = _factor("IML_DCF_PENALTY_REVIEW", 0.88)
    caution_factor = _factor("IML_DCF_PENALTY_CAUTION", 0.94)
    cross_warn_factor = _factor("IML_DCF_PENALTY_CROSSCHECK_WARN", 0.95)
    min_floor = _factor("IML_DCF_PENALTY_MIN_FLOOR", 0.75, min_value=0.5, max_value=1.0)

    multiplier = 1.0
    status = (quality_gate_status or "").strip().lower()
    cross = (comps_crosscheck_status or "").strip().lower()
    if status == "review":
        multiplier *= review_factor
    elif status == "caution":
        multiplier *= caution_factor
    if cross == "warn":
        multiplier *= cross_warn_factor
    return max(min_floor, min(multiplier, 1.0))


def _dcf_quality_penalty_rule_text() -> str:
    review_factor = str(os.getenv("IML_DCF_PENALTY_REVIEW", "0.88")).strip() or "0.88"
    caution_factor = str(os.getenv("IML_DCF_PENALTY_CAUTION", "0.94")).strip() or "0.94"
    cross_warn_factor = str(os.getenv("IML_DCF_PENALTY_CROSSCHECK_WARN", "0.95")).strip() or "0.95"
    min_floor = str(os.getenv("IML_DCF_PENALTY_MIN_FLOOR", "0.75")).strip() or "0.75"
    return (
        "default 1.0; "
        f"quality_gate(review={review_factor},caution={caution_factor}) "
        f"× comps_crosscheck(warn={cross_warn_factor}); floor={min_floor}"
    )


def _pull_dcf_portfolio(
    dcf_link_script: Path,
    dcf_base_url: str,
    dcf_timeout: float,
    symbols: List[str],
    transport_meta: Dict[str, Any] | None = None,
) -> Dict[str, DCFValuation]:
    if not symbols:
        return {}
    cmd = [
        "python3",
        str(dcf_link_script),
        "--mode",
        "portfolio",
        "--base-url",
        dcf_base_url,
        "--symbols",
        ",".join(symbols),
        "--format",
        "json",
        "--timeout",
        str(dcf_timeout),
    ]
    payload = _run_dcf_link_with_env(cmd, dcf_base_url=dcf_base_url)
    if transport_meta is not None:
        requested = str(payload.get("base_url_requested") or dcf_base_url).strip() or dcf_base_url
        effective = str(payload.get("base_url") or requested).strip() or requested
        probes = payload.get("base_url_probe")
        transport_meta["base_url_requested"] = requested
        transport_meta["base_url_effective"] = effective
        transport_meta["base_url_probe"] = probes if isinstance(probes, list) else []
    result: Dict[str, DCFValuation] = {}
    for company in payload.get("companies", []):
        if not isinstance(company, dict):
            continue
        parsed = _parse_dcf_company_payload(company)
        if parsed is None:
            continue
        result[parsed.symbol] = parsed
    return result


def _pull_dcf_companies_individually(
    dcf_link_script: Path,
    dcf_base_url: str,
    dcf_timeout: float,
    symbols: List[str],
    transport_meta: Dict[str, Any] | None = None,
) -> tuple[Dict[str, DCFValuation], List[str]]:
    result: Dict[str, DCFValuation] = {}
    failures: List[str] = []
    for symbol in symbols:
        cmd = [
            "python3",
            str(dcf_link_script),
            "--mode",
            "company",
            "--base-url",
            dcf_base_url,
            "--symbol",
            symbol,
            "--format",
            "json",
            "--timeout",
            str(dcf_timeout),
        ]
        try:
            payload = _run_dcf_link_with_env(cmd, dcf_base_url=dcf_base_url)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{symbol}: {exc}")
            continue
        if transport_meta is not None:
            requested = str(payload.get("base_url_requested") or dcf_base_url).strip() or dcf_base_url
            effective = str(payload.get("base_url") or requested).strip() or requested
            probes = payload.get("base_url_probe")
            transport_meta["base_url_requested"] = requested
            transport_meta["base_url_effective"] = effective
            transport_meta["base_url_probe"] = probes if isinstance(probes, list) else []
        parsed = _parse_dcf_company_payload(payload)
        if parsed is None:
            failures.append(f"{symbol}: missing valuation payload")
            continue
        result[symbol] = parsed
    return result, failures


def _apply_non_dcf_valuation(row: RawMarketRow, reason: str) -> None:
    if row.target_mean_price and row.target_mean_price > 0:
        row.fair_value = row.target_mean_price
        row.valuation_source = "target_mean_price"
        row.valuation_source_detail = f"yahoo_target_mean_price({reason})"
    else:
        row.fair_value = row.close
        row.valuation_source = "close_fallback"
        row.valuation_source_detail = f"close_fallback({reason})"
    row.dcf_iv_base = None
    row.dcf_mos_base = None
    row.dcf_price = None
    row.dcf_status = None
    row.dcf_pulled_at = None
    row.dcf_quality_gate_status = None
    row.dcf_quality_gate_score = None
    row.dcf_quality_gate_issues = ""
    row.dcf_comps_crosscheck_status = None
    row.dcf_comps_deviation_vs_median = None
    row.dcf_comps_source = None
    row.dcf_quality_penalty_multiplier = 1.0


def apply_dcf_overlay(
    raw_rows: List[RawMarketRow],
    *,
    enable_dcf: bool,
    dcf_link_script: Path,
    dcf_companies_file: Path,
    dcf_base_url: str,
    dcf_timeout: float,
    dcf_strict: bool,
) -> Dict[str, Any]:
    ticker_to_symbol: Dict[str, str] = {}
    dcf_errors: List[str] = []
    unresolved_tickers: List[str] = []
    covered_tickers: List[str] = []
    covered_iv_tickers: List[str] = []
    covered_consensus_tickers: List[str] = []
    quality_gate_status_counts: Dict[str, int] = {}
    comps_crosscheck_status_counts: Dict[str, int] = {}
    pulled_valuations: Dict[str, DCFValuation] = {}
    dcf_transport_meta: Dict[str, Any] = {
        "base_url_requested": dcf_base_url,
        "base_url_effective": dcf_base_url,
        "base_url_probe": [],
    }

    available_symbols = _load_dcf_available_symbols(dcf_companies_file)
    if enable_dcf:
        for row in raw_rows:
            resolved = resolve_dcf_symbol(row.ticker, available_symbols)
            if resolved is None and available_symbols is None:
                resolved = resolve_dcf_symbol(row.ticker, None)
            if resolved is None:
                unresolved_tickers.append(row.ticker)
                continue
            ticker_to_symbol[row.ticker] = resolved

        if not dcf_link_script.exists():
            dcf_errors.append(f"dcf_link_script_not_found: {dcf_link_script}")
            if dcf_strict:
                raise RuntimeError(dcf_errors[-1])
        else:
            target_symbols = sorted(set(ticker_to_symbol.values()))
            try:
                if available_symbols:
                    pulled_valuations = _pull_dcf_portfolio(
                        dcf_link_script=dcf_link_script,
                        dcf_base_url=dcf_base_url,
                        dcf_timeout=dcf_timeout,
                        symbols=target_symbols,
                        transport_meta=dcf_transport_meta,
                    )
                else:
                    pulled_valuations, dcf_errors = _pull_dcf_companies_individually(
                        dcf_link_script=dcf_link_script,
                        dcf_base_url=dcf_base_url,
                        dcf_timeout=dcf_timeout,
                        symbols=target_symbols,
                        transport_meta=dcf_transport_meta,
                    )
            except Exception as exc:  # noqa: BLE001
                dcf_errors.append(str(exc))
                if dcf_strict:
                    raise

    for row in raw_rows:
        row.dcf_symbol = ticker_to_symbol.get(row.ticker)
        valuation = pulled_valuations.get(row.dcf_symbol or "")
        if enable_dcf and valuation is not None and valuation.iv_base is not None and valuation.iv_base > 0:
            row.fair_value = valuation.iv_base
            row.valuation_source = "dcf_iv_base"
            row.valuation_source_detail = f"{valuation.symbol}:iv_base"
            row.dcf_iv_base = valuation.iv_base
            row.dcf_mos_base = valuation.mos_base
            row.dcf_price = valuation.price
            row.dcf_status = valuation.status
            row.dcf_pulled_at = valuation.pulled_at
            row.dcf_quality_gate_status = valuation.quality_gate_status
            row.dcf_quality_gate_score = valuation.quality_gate_score
            row.dcf_quality_gate_issues = ";".join(valuation.quality_gate_issues or [])
            row.dcf_comps_crosscheck_status = valuation.comps_crosscheck_status
            row.dcf_comps_deviation_vs_median = valuation.comps_crosscheck_deviation
            row.dcf_comps_source = valuation.comps_crosscheck_source
            row.dcf_quality_penalty_multiplier = _dcf_quality_penalty_multiplier(
                quality_gate_status=valuation.quality_gate_status,
                comps_crosscheck_status=valuation.comps_crosscheck_status,
            )
            covered_tickers.append(row.ticker)
            covered_iv_tickers.append(row.ticker)
        elif (
            enable_dcf
            and valuation is not None
            and valuation.consensus_fair_value is not None
            and valuation.consensus_fair_value > 0
        ):
            row.fair_value = valuation.consensus_fair_value
            row.valuation_source = "dcf_external_consensus"
            row.valuation_source_detail = f"{valuation.symbol}:consensus_median"
            row.dcf_iv_base = valuation.iv_base
            row.dcf_mos_base = valuation.mos_base
            row.dcf_price = valuation.price
            row.dcf_status = valuation.status
            row.dcf_pulled_at = valuation.pulled_at
            row.dcf_quality_gate_status = valuation.quality_gate_status
            row.dcf_quality_gate_score = valuation.quality_gate_score
            row.dcf_quality_gate_issues = ";".join(valuation.quality_gate_issues or [])
            row.dcf_comps_crosscheck_status = valuation.comps_crosscheck_status
            row.dcf_comps_deviation_vs_median = valuation.comps_crosscheck_deviation
            row.dcf_comps_source = valuation.comps_crosscheck_source
            row.dcf_quality_penalty_multiplier = _dcf_quality_penalty_multiplier(
                quality_gate_status=valuation.quality_gate_status,
                comps_crosscheck_status=valuation.comps_crosscheck_status,
            )
            covered_tickers.append(row.ticker)
            covered_consensus_tickers.append(row.ticker)
        else:
            reason = "dcf_disabled"
            if enable_dcf:
                reason = "dcf_symbol_unavailable" if row.dcf_symbol is None else "dcf_missing_payload"
            _apply_non_dcf_valuation(row, reason=reason)

        row.note = _build_note(
            base_note=row.base_note,
            as_of_date=row.as_of_date,
            close=row.close,
            target_mean=row.target_mean_price,
            fair_value=row.fair_value,
            valuation_source=row.valuation_source,
            dcf_symbol=row.dcf_symbol,
            dcf_iv_base=row.dcf_iv_base,
        )
        if row.dcf_quality_gate_status:
            key = str(row.dcf_quality_gate_status).lower()
            quality_gate_status_counts[key] = quality_gate_status_counts.get(key, 0) + 1
        if row.dcf_comps_crosscheck_status:
            key = str(row.dcf_comps_crosscheck_status).lower()
            comps_crosscheck_status_counts[key] = comps_crosscheck_status_counts.get(key, 0) + 1

    source_counts: Dict[str, int] = {}
    for row in raw_rows:
        source_counts[row.valuation_source] = source_counts.get(row.valuation_source, 0) + 1

    return {
        "enabled": enable_dcf,
        "dcf_link_script": str(dcf_link_script),
        "dcf_companies_file": str(dcf_companies_file),
        "dcf_base_url": dcf_base_url,
        "dcf_base_url_requested": dcf_transport_meta.get("base_url_requested", dcf_base_url),
        "dcf_base_url_effective": dcf_transport_meta.get("base_url_effective", dcf_base_url),
        "dcf_base_url_probe": dcf_transport_meta.get("base_url_probe", []),
        "available_symbols_count": len(available_symbols or []),
        "requested_symbols": sorted(set(ticker_to_symbol.values())),
        "pulled_symbols": sorted(pulled_valuations.keys()),
        "covered_tickers": sorted(covered_tickers),
        "covered_iv_tickers": sorted(covered_iv_tickers),
        "covered_consensus_tickers": sorted(covered_consensus_tickers),
        "unresolved_tickers": sorted(unresolved_tickers),
        "errors": dcf_errors,
        "valuation_source_counts": source_counts,
        "quality_gate_status_counts": quality_gate_status_counts,
        "comps_crosscheck_status_counts": comps_crosscheck_status_counts,
        "coverage_ratio": (len(covered_tickers) / len(raw_rows)) if raw_rows else 0.0,
        "iv_coverage_ratio": (len(covered_iv_tickers) / len(raw_rows)) if raw_rows else 0.0,
    }


def _build_note(
    base_note: str,
    as_of_date: str,
    close: float,
    target_mean: float | None,
    fair_value: float,
    valuation_source: str,
    dcf_symbol: str | None,
    dcf_iv_base: float | None,
) -> str:
    price_upside = (fair_value / close - 1.0) if close > 0 else 0.0
    note_parts = [base_note.strip()]
    note_parts.append(f"real-data@{as_of_date}")
    note_parts.append(f"close={close:.2f}")
    if target_mean and target_mean > 0:
        note_parts.append(f"target={target_mean:.2f}")
    else:
        note_parts.append("target=NA(fallback-close)")
    note_parts.append(f"fv_source={valuation_source}")
    if dcf_symbol:
        note_parts.append(f"dcf_symbol={dcf_symbol}")
    if dcf_iv_base is not None and dcf_iv_base > 0:
        note_parts.append(f"dcf_iv={dcf_iv_base:.2f}")
    note_parts.append(f"upside={price_upside * 100:.1f}%")
    return " | ".join(part for part in note_parts if part)


def _cache_key(ticker: str, history_period: str) -> str:
    raw = f"{ticker}_{history_period}"
    return "".join(ch if ch.isalnum() else "_" for ch in raw).lower()


def _cache_path(cache_dir: Path, ticker: str, history_period: str) -> Path:
    return cache_dir / f"{_cache_key(ticker, history_period)}.json"


def _load_cached_row(
    cache_file: Path,
    ttl_hours: int,
    history_period: str,
) -> RawMarketRow | None:
    if ttl_hours <= 0 or not cache_file.exists():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at_raw = payload.get("cached_at_utc")
        cached_period = payload.get("history_period")
        row_data = payload.get("row")
        if not cached_at_raw or not isinstance(row_data, dict):
            return None
        if cached_period and cached_period != history_period:
            return None
        cached_at = datetime.fromisoformat(str(cached_at_raw))
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
            return None
        return RawMarketRow(**row_data)
    except Exception:  # noqa: BLE001
        return None


def _save_cached_row(cache_file: Path, history_period: str, row: RawMarketRow) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at_utc": datetime.now(timezone.utc).isoformat(),
        "history_period": history_period,
        "row": asdict(row),
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_raw_market_row(item: Dict[str, str], history_period: str) -> RawMarketRow:
    ticker = (item.get("ticker") or "").strip()
    if not ticker:
        raise ValueError("Universe row missing ticker")
    yf_ticker = YF_TICKER_MAP.get(ticker, normalize_yf_ticker(ticker))
    snapshot_quote = get_snapshot_record("quotes", ticker)
    snapshot_external = get_snapshot_record("external_valuations", ticker)
    snapshot_fundamental = get_snapshot_record("fundamentals", ticker)

    if _stock_data_hub_url() is None:
        raise ValueError("IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode")
    info = {}
    closes = fetch_price_history_from_stock_data_hub(ticker=ticker, period=history_period, interval="1d")

    hub_quote = None
    if closes.empty:
        if isinstance(snapshot_quote, dict):
            snapshot_price = _safe_float(snapshot_quote.get("price"))
            if snapshot_price is not None and snapshot_price > 0:
                as_of_raw = str(snapshot_quote.get("as_of") or "").strip()
                as_of_date = as_of_raw[:10] if len(as_of_raw) >= 10 else datetime.now(timezone.utc).date().isoformat()
                close = float(snapshot_price)
                hub_quote = {
                    "price": close,
                    "as_of_date": as_of_date,
                    "provider": str(snapshot_quote.get("provider") or "stock_data_hub_snapshot"),
                    "quality_flag": str(snapshot_quote.get("quality_flag") or ""),
                }
            else:
                hub_quote = None
        if hub_quote is None:
            hub_quote = fetch_quote_from_stock_data_hub(ticker=ticker, timeout_sec=8.0)
        if hub_quote is None:
            raise ValueError(f"{ticker}: missing close history from stock-data-hub")
        as_of_date = hub_quote["as_of_date"]
        close = float(hub_quote["price"])
    else:
        as_of_date = closes.index[-1].date().isoformat()
        close = float(closes.iloc[-1])

    yf_target_mean = _safe_float(info.get("targetMeanPrice"))
    hub_external = None
    need_external = (
        yf_target_mean is None
        or yf_target_mean <= 0
        or _safe_float(info.get("numberOfAnalystOpinions")) is None
        or _safe_float(info.get("recommendationMean")) is None
    )
    if need_external:
        if isinstance(snapshot_external, dict):
            hub_external = {
                "provider": str(snapshot_external.get("provider") or "stock_data_hub_snapshot"),
                "target_mean_price": _safe_float(snapshot_external.get("target_mean_price")),
                "target_median_price": _safe_float(snapshot_external.get("target_median_price")),
                "target_high_price": _safe_float(snapshot_external.get("target_high_price")),
                "target_low_price": _safe_float(snapshot_external.get("target_low_price")),
                "analyst_count": _safe_float(snapshot_external.get("analyst_count")),
                "recommendation_mean": _first_valid(
                    snapshot_external.get("recommendation_mean"),
                    snapshot_external.get("target_rating_mean"),
                ),
            }
        if hub_external is None:
            hub_external = fetch_external_valuation_from_stock_data_hub(ticker=ticker, timeout_sec=8.0)
    target_mean, valuation_source = _target_from_sources(yf_target=yf_target_mean, hub_external=hub_external)
    fair_value = target_mean if target_mean and target_mean > 0 else close

    hub_fundamental = None
    if not info or (
        _safe_float(info.get("returnOnEquity")) is None
        and _safe_float(info.get("grossMargins")) is None
        and _safe_float(info.get("operatingMargins")) is None
        and _safe_float(info.get("revenueGrowth")) is None
        and _safe_float(info.get("earningsGrowth")) is None
    ):
        if isinstance(snapshot_fundamental, dict):
            hub_fundamental = {
                "provider": str(snapshot_fundamental.get("provider") or "stock_data_hub_snapshot"),
                "return_on_equity": _safe_float(snapshot_fundamental.get("return_on_equity")),
                "gross_margins": _safe_float(snapshot_fundamental.get("gross_margin")),
                "operating_margins": _safe_float(snapshot_fundamental.get("operating_margin")),
                "revenue_growth": _safe_float(snapshot_fundamental.get("revenue_growth")),
                "earnings_growth": _safe_float(snapshot_fundamental.get("earnings_growth")),
                "debt_to_equity": _safe_float(snapshot_fundamental.get("debt_to_equity")),
                "analyst_count": _safe_float(snapshot_fundamental.get("analyst_count")),
            }
        if hub_fundamental is None:
            hub_fundamental = fetch_fundamental_from_stock_data_hub(ticker=ticker, timeout_sec=8.0)
    quality_fields = _calc_quality_fields(info=info, hub_fundamental=hub_fundamental, hub_external=hub_external)
    if quality_fields.get("analyst_count") is None and hub_external is not None:
        quality_fields["analyst_count"] = _normalize_analyst_count(_safe_float(hub_external.get("analyst_count")))

    if closes.empty:
        ret_3m = None
        ret_6m = None
        ret_12m = None
        dist_to_sma200 = None
        vol_1y = None
        max_drawdown_1y = None
    else:
        ret_3m = _calc_return(closes, 63)
        ret_6m = _calc_return(closes, 126)
        ret_12m = _calc_return(closes, 252)

        sma200 = float(closes.tail(200).mean()) if len(closes) >= 30 else float(closes.mean())
        dist_to_sma200 = (close / sma200 - 1.0) if sma200 else None

        returns = closes.pct_change().dropna().tail(252)
        vol_1y = float(returns.std() * math.sqrt(252)) if not returns.empty else None
        max_drawdown_1y = _calc_max_drawdown(closes.tail(252))

    note = _build_note(
        base_note=item.get("note", ""),
        as_of_date=as_of_date,
        close=close,
        target_mean=target_mean,
        fair_value=fair_value,
        valuation_source=valuation_source,
        dcf_symbol=None,
        dcf_iv_base=None,
    )

    return RawMarketRow(
        ticker=ticker,
        yf_ticker=yf_ticker,
        name=_build_row_name(item=item, info=info, ticker=ticker),
        sector=_build_row_sector(item=item, info=info),
        as_of_date=as_of_date,
        close=close,
        fair_value=fair_value,
        target_mean_price=target_mean,
        return_on_equity=quality_fields.get("return_on_equity"),
        gross_margins=quality_fields.get("gross_margins"),
        operating_margins=quality_fields.get("operating_margins"),
        revenue_growth=quality_fields.get("revenue_growth"),
        earnings_growth=quality_fields.get("earnings_growth"),
        earnings_quarterly_growth=quality_fields.get("earnings_quarterly_growth"),
        debt_to_equity=quality_fields.get("debt_to_equity"),
        beta=quality_fields.get("beta"),
        analyst_count=quality_fields.get("analyst_count"),
        recommendation_mean=quality_fields.get("recommendation_mean"),
        ret_3m=ret_3m,
        ret_6m=ret_6m,
        ret_12m=ret_12m,
        dist_to_sma200=dist_to_sma200,
        vol_1y=vol_1y,
        max_drawdown_1y=max_drawdown_1y,
        note=note,
        valuation_source=valuation_source,
        valuation_source_detail=_build_valuation_detail(
            valuation_source=valuation_source,
            yf_target=yf_target_mean,
            hub_external=hub_external,
            hub_quote=hub_quote,
        ),
        base_note=item.get("note", ""),
        data_lineage="hub_only(price_history+quote+fundamental+external)",
    )


def fetch_raw_market_row_with_timeout(
    item: Dict[str, str],
    history_period: str,
    timeout_seconds: float,
) -> RawMarketRow:
    if timeout_seconds <= 0:
        return fetch_raw_market_row(item, history_period=history_period)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fetch_raw_market_row, item, history_period)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            ticker = (item.get("ticker") or "").strip() or "UNKNOWN"
            raise TimeoutError(f"{ticker}: fetch timeout>{timeout_seconds:.1f}s") from exc


def fetch_raw_market_row_with_retries(
    item: Dict[str, str],
    history_period: str,
    timeout_seconds: float,
    retries: int,
    timeout_multiplier: float,
    retry_backoff_seconds: float,
) -> RawMarketRow:
    attempts = max(1, int(retries) + 1)
    current_timeout = max(0.1, float(timeout_seconds))
    grow = max(1.0, float(timeout_multiplier))
    backoff = max(0.0, float(retry_backoff_seconds))
    last_exc: Exception | None = None

    for attempt in range(attempts):
        try:
            return fetch_raw_market_row_with_timeout(
                item,
                history_period=history_period,
                timeout_seconds=current_timeout,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= attempts - 1:
                break
            if backoff > 0:
                time.sleep(backoff * (attempt + 1))
            current_timeout = max(current_timeout, current_timeout * grow)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unknown fetch failure")


def percentile_score(series: pd.Series, higher_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.notna().sum() == 0:
        return pd.Series([50.0] * len(values), index=values.index, dtype=float)
    ranked = values.rank(pct=True, ascending=not higher_better)
    return (ranked * 100.0).fillna(50.0).clip(0.0, 100.0)


def weighted_mean(df: pd.DataFrame, weighted_cols: List[tuple[str, float]]) -> pd.Series:
    total_weight = sum(weight for _, weight in weighted_cols)
    if total_weight <= 0:
        return pd.Series([50.0] * len(df), index=df.index, dtype=float)

    result = pd.Series([0.0] * len(df), index=df.index, dtype=float)
    for column, weight in weighted_cols:
        result += df[column].fillna(50.0) * weight
    return (result / total_weight).clip(0.0, 100.0)


def build_scored_frame(raw_rows: List[RawMarketRow]) -> pd.DataFrame:
    df = pd.DataFrame([row.__dict__ for row in raw_rows])
    df["price_to_fair_value"] = df["close"] / df["fair_value"]

    df["q_roe"] = percentile_score(df["return_on_equity"], higher_better=True)
    df["q_gross_margin"] = percentile_score(df["gross_margins"], higher_better=True)
    df["q_operating_margin"] = percentile_score(df["operating_margins"], higher_better=True)
    df["q_debt"] = percentile_score(df["debt_to_equity"], higher_better=False)
    df["quality_score"] = weighted_mean(
        df,
        [
            ("q_roe", 0.30),
            ("q_gross_margin", 0.25),
            ("q_operating_margin", 0.25),
            ("q_debt", 0.20),
        ],
    )

    df["g_revenue"] = percentile_score(df["revenue_growth"], higher_better=True)
    df["g_earnings"] = percentile_score(df["earnings_growth"], higher_better=True)
    df["g_quarterly"] = percentile_score(df["earnings_quarterly_growth"], higher_better=True)
    df["growth_score"] = weighted_mean(
        df,
        [
            ("g_revenue", 0.35),
            ("g_earnings", 0.35),
            ("g_quarterly", 0.30),
        ],
    )

    df["m_ret_3m"] = percentile_score(df["ret_3m"], higher_better=True)
    df["m_ret_6m"] = percentile_score(df["ret_6m"], higher_better=True)
    df["m_ret_12m"] = percentile_score(df["ret_12m"], higher_better=True)
    df["m_dist_200"] = percentile_score(df["dist_to_sma200"], higher_better=True)
    df["momentum_score"] = weighted_mean(
        df,
        [
            ("m_ret_3m", 0.25),
            ("m_ret_6m", 0.25),
            ("m_ret_12m", 0.30),
            ("m_dist_200", 0.20),
        ],
    )

    df["c_upside"] = percentile_score((df["fair_value"] / df["close"] - 1.0), higher_better=True)
    df["c_recommend"] = percentile_score(df["recommendation_mean"], higher_better=False)
    df["c_quarterly"] = percentile_score(df["earnings_quarterly_growth"], higher_better=True)
    df["c_analyst_count"] = percentile_score(df["analyst_count"], higher_better=True)
    df["catalyst_score"] = weighted_mean(
        df,
        [
            ("c_upside", 0.35),
            ("c_recommend", 0.25),
            ("c_quarterly", 0.25),
            ("c_analyst_count", 0.15),
        ],
    )

    df["r_vol"] = percentile_score(df["vol_1y"], higher_better=True)
    df["r_mdd"] = percentile_score(df["max_drawdown_1y"], higher_better=True)
    df["r_beta"] = percentile_score(df["beta"], higher_better=True)
    df["r_debt"] = percentile_score(df["debt_to_equity"], higher_better=True)
    df["risk_score"] = weighted_mean(
        df,
        [
            ("r_vol", 0.35),
            ("r_mdd", 0.35),
            ("r_beta", 0.20),
            ("r_debt", 0.10),
        ],
    )

    df["risk_control_proxy"] = (100.0 - df["risk_score"]).clip(0.0, 100.0)
    df["certainty_score"] = weighted_mean(
        df,
        [
            ("quality_score", 0.45),
            ("risk_control_proxy", 0.35),
            ("c_analyst_count", 0.20),
        ],
    )
    return df


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = default
    return max(min_value, min(parsed, max_value))


def _env_text(name: str, default: str) -> str:
    raw = str(os.getenv(name, default)).strip()
    return raw or default


def _hub_symbol_for_row(row: RawMarketRow) -> str:
    if row.dcf_symbol:
        return str(row.dcf_symbol).strip().upper()
    return str(row.ticker).strip().upper()


def _market_from_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if raw.startswith(("SH.", "SZ.")) or raw.endswith((".SS", ".SZ")):
        return "A"
    if raw.startswith("HK.") or raw.endswith(".HK"):
        return "HK"
    return "US"


def _pick_primary_comps_deviation(metrics: Any) -> float | None:
    if not isinstance(metrics, dict):
        return None
    for key in (
        "trailing_pe",
        "forward_pe",
        "price_to_book",
        "ev_to_fcf",
        "ev_to_ocf",
        "ev_to_market_cap",
    ):
        item = metrics.get(key)
        if not isinstance(item, dict):
            continue
        deviation = _safe_float(item.get("deviation_pct"))
        if deviation is not None:
            return deviation
    return None


def _symbol_aliases(symbol: str) -> set[str]:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        return set()
    aliases = {normalized}
    for alias in dcf_symbol_candidates(normalized):
        aliases.add(str(alias).strip().upper())
    if normalized.startswith("US.") and "." in normalized:
        aliases.add(normalized.split(".", 1)[1].strip().upper())
    return {item for item in aliases if item}


def _fetch_hub_market_caps(symbols: list[str], timeout_sec: float) -> dict[str, float]:
    payload = _hub_post_json(
        path="v1/fundamentals",
        payload={
            "symbols": symbols,
            "mode": "non_realtime",
            "refresh": False,
        },
        timeout_sec=timeout_sec,
    )
    if not isinstance(payload, dict):
        return {}
    records = payload.get("items")
    if not isinstance(records, list):
        return {}

    caps: dict[str, float] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        market_cap = _safe_float(item.get("market_cap"))
        if not symbol or market_cap is None or market_cap <= 0:
            continue
        for alias in _symbol_aliases(symbol):
            caps[alias] = market_cap
    return caps


def _size_distance(lhs: float | None, rhs: float | None) -> float:
    if lhs is None or rhs is None or lhs <= 0 or rhs <= 0:
        return 99.0
    return abs(math.log(lhs) - math.log(rhs))


def _build_hub_comps_batch_items(
    raw_rows: List[RawMarketRow],
    *,
    max_peers: int,
    min_peers: int,
    peer_strategy: str = "sector_market",
    market_caps: dict[str, float] | None = None,
) -> tuple[list[dict[str, object]], dict[str, RawMarketRow], int]:
    entries: list[dict[str, object]] = []
    symbol_seen: set[str] = set()
    for row in raw_rows:
        symbol = _hub_symbol_for_row(row)
        if not symbol or symbol in symbol_seen:
            continue
        symbol_seen.add(symbol)
        entries.append(
            {
                "row": row,
                "symbol": symbol,
                "market": _market_from_symbol(symbol),
                "sector_key": str(row.sector or "Unknown").strip().lower() or "unknown",
                "market_cap": _safe_float((market_caps or {}).get(symbol)),
            }
        )

    items: list[dict[str, object]] = []
    symbol_to_row: dict[str, RawMarketRow] = {}
    skipped_existing = 0
    for entry in entries:
        row = entry["row"]
        if not isinstance(row, RawMarketRow):
            continue
        if str(row.dcf_comps_crosscheck_status or "").strip():
            skipped_existing += 1
            continue

        symbol = str(entry["symbol"])
        market = str(entry["market"])
        sector_key = str(entry["sector_key"])
        target_cap = _safe_float(entry.get("market_cap"))
        candidates = [
            other
            for other in entries
            if other["symbol"] != symbol and other["market"] == market
        ]
        if peer_strategy == "sector_size":
            sorted_candidates = sorted(
                candidates,
                key=lambda other: (
                    0 if other.get("sector_key") == sector_key else 1,
                    _size_distance(target_cap, _safe_float(other.get("market_cap"))),
                    str(other.get("symbol") or ""),
                ),
            )
            peers = [str(other["symbol"]) for other in sorted_candidates[:max_peers]]
        else:
            same_market_sector = [
                str(other["symbol"])
                for other in entries
                if other["symbol"] != symbol and other["market"] == market and other["sector_key"] == sector_key
            ]
            same_market = [
                str(other["symbol"])
                for other in entries
                if other["symbol"] != symbol and other["market"] == market and str(other["symbol"]) not in same_market_sector
            ]
            peers = (same_market_sector + same_market)[:max_peers]
        if len(peers) < min_peers:
            continue
        items.append({"symbol": symbol, "peers": peers})
        for alias in _symbol_aliases(symbol):
            if alias:
                symbol_to_row[alias] = row
    return items, symbol_to_row, skipped_existing


def apply_hub_comps_overlay(raw_rows: List[RawMarketRow]) -> Dict[str, Any]:
    base_url = _stock_data_hub_url()
    if not base_url:
        return {
            "enabled": False,
            "reason": "stock_data_hub_url_missing",
        }
    if str(os.getenv("IML_DISABLE_HUB_COMPS_OVERLAY", "")).strip() in {"1", "true", "TRUE", "yes", "YES"}:
        return {
            "enabled": False,
            "reason": "disabled_by_env",
            "base_url": base_url,
        }

    max_peers = _env_int("IML_HUB_COMPS_PEER_MAX", 6, min_value=2, max_value=12)
    min_peers = _env_int("IML_HUB_COMPS_PEER_MIN", 2, min_value=1, max_value=max_peers)
    timeout_sec = _safe_float(os.getenv("IML_HUB_COMPS_TIMEOUT", "15")) or 15.0
    peer_strategy = _env_text("IML_HUB_COMPS_PEER_STRATEGY", "sector_market").lower()
    if peer_strategy not in {"sector_market", "sector_size"}:
        peer_strategy = "sector_market"

    market_caps: dict[str, float] = {}
    if peer_strategy == "sector_size":
        symbol_candidates = sorted({_hub_symbol_for_row(row) for row in raw_rows if _hub_symbol_for_row(row)})
        market_caps = _fetch_hub_market_caps(symbol_candidates, timeout_sec=timeout_sec)

    items, symbol_to_row, skipped_existing = _build_hub_comps_batch_items(
        raw_rows,
        max_peers=max_peers,
        min_peers=min_peers,
        peer_strategy=peer_strategy,
        market_caps=market_caps,
    )
    cap_covered = 0
    if peer_strategy == "sector_size":
        for row in raw_rows:
            symbol = _hub_symbol_for_row(row)
            if any(alias in market_caps for alias in _symbol_aliases(symbol)):
                cap_covered += 1
    meta: Dict[str, Any] = {
        "enabled": True,
        "base_url": base_url,
        "request_count": len(items),
        "skipped_existing_count": skipped_existing,
        "max_peers": max_peers,
        "min_peers": min_peers,
        "peer_strategy": peer_strategy,
        "market_cap_covered_count": cap_covered,
        "market_cap_coverage_ratio": (cap_covered / len(raw_rows)) if raw_rows else 0.0,
        "applied_count": 0,
        "failed_count": 0,
        "status_counts": {},
    }
    if not items:
        meta["reason"] = "no_eligible_items"
        return meta

    payload = _hub_post_json(
        path="v1/comps-baselines",
        payload={
            "items": items,
            "mode": "non_realtime",
            "refresh": False,
        },
        timeout_sec=timeout_sec,
    )
    if not isinstance(payload, dict):
        meta["reason"] = "request_failed"
        return meta

    records = payload.get("items")
    failed = payload.get("failed")
    if not isinstance(records, list):
        records = []
    if not isinstance(failed, dict):
        failed = {}

    status_counts: Dict[str, int] = {}
    applied = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        symbol = str(record.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        row = symbol_to_row.get(symbol)
        if row is None:
            continue
        status_raw = str(record.get("status") or "").strip().lower()
        if not status_raw:
            continue
        if str(row.dcf_comps_crosscheck_status or "").strip():
            continue

        row.dcf_comps_crosscheck_status = status_raw
        row.dcf_comps_deviation_vs_median = _pick_primary_comps_deviation(record.get("metrics"))
        row.dcf_comps_source = "stock_data_hub_comps_baseline"
        if row.valuation_source in {"dcf_iv_base", "dcf_external_consensus"}:
            row.dcf_quality_penalty_multiplier = _dcf_quality_penalty_multiplier(
                quality_gate_status=row.dcf_quality_gate_status,
                comps_crosscheck_status=row.dcf_comps_crosscheck_status,
            )
        status_counts[status_raw] = status_counts.get(status_raw, 0) + 1
        applied += 1

    meta["applied_count"] = applied
    meta["failed_count"] = len(failed)
    meta["failed"] = failed
    meta["status_counts"] = status_counts
    return meta


def _format_float(value: Any, digits: int = 4) -> str:
    parsed = _safe_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.{digits}f}"


def _format_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def write_real_opportunities(path: Path, df: pd.DataFrame, ordered_tickers: List[str]) -> None:
    fieldnames = [
        "ticker",
        "name",
        "sector",
        "price_to_fair_value",
        "fair_value",
        "target_mean_price",
        "valuation_source",
        "valuation_source_detail",
        "dcf_symbol",
        "dcf_iv_base",
        "dcf_mos_base",
        "dcf_price",
        "dcf_status",
        "dcf_quality_gate_status",
        "dcf_quality_gate_score",
        "dcf_quality_gate_issues",
        "dcf_comps_crosscheck_status",
        "dcf_comps_deviation_vs_median",
        "dcf_comps_source",
        "dcf_quality_penalty_multiplier",
        "quality_score",
        "growth_score",
        "momentum_score",
        "catalyst_score",
        "risk_score",
        "certainty_score",
        "data_lineage",
        "note",
    ]
    row_map = {row["ticker"]: row for _, row in df.iterrows()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for ticker in ordered_tickers:
            if ticker not in row_map:
                continue
            row = row_map[ticker]
            writer.writerow(
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "sector": row["sector"],
                    "price_to_fair_value": _format_float(row.get("price_to_fair_value"), digits=4),
                    "fair_value": _format_float(row.get("fair_value"), digits=4),
                    "target_mean_price": _format_float(row.get("target_mean_price"), digits=4),
                    "valuation_source": _format_text(row.get("valuation_source")),
                    "valuation_source_detail": _format_text(row.get("valuation_source_detail")),
                    "dcf_symbol": _format_text(row.get("dcf_symbol")),
                    "dcf_iv_base": _format_float(row.get("dcf_iv_base"), digits=4),
                    "dcf_mos_base": _format_float(row.get("dcf_mos_base"), digits=4),
                    "dcf_price": _format_float(row.get("dcf_price"), digits=4),
                    "dcf_status": _format_text(row.get("dcf_status")),
                    "dcf_quality_gate_status": _format_text(row.get("dcf_quality_gate_status")),
                    "dcf_quality_gate_score": _format_float(row.get("dcf_quality_gate_score"), digits=2),
                    "dcf_quality_gate_issues": _format_text(row.get("dcf_quality_gate_issues")),
                    "dcf_comps_crosscheck_status": _format_text(row.get("dcf_comps_crosscheck_status")),
                    "dcf_comps_deviation_vs_median": _format_float(
                        row.get("dcf_comps_deviation_vs_median"), digits=4
                    ),
                    "dcf_comps_source": _format_text(row.get("dcf_comps_source")),
                    "dcf_quality_penalty_multiplier": _format_float(
                        row.get("dcf_quality_penalty_multiplier"), digits=4
                    ),
                    "quality_score": f"{float(row['quality_score']):.1f}",
                    "growth_score": f"{float(row['growth_score']):.1f}",
                    "momentum_score": f"{float(row['momentum_score']):.1f}",
                    "catalyst_score": f"{float(row['catalyst_score']):.1f}",
                    "risk_score": f"{float(row['risk_score']):.1f}",
                    "certainty_score": f"{float(row['certainty_score']):.1f}",
                    "data_lineage": _format_text(row.get("data_lineage")),
                    "note": row["note"],
                }
            )


def write_meta(
    path: Path,
    df: pd.DataFrame,
    generated_at: str,
    cache_enabled: bool,
    cache_ttl_hours: int,
    dcf_meta: Dict[str, Any],
    hub_comps_meta: Dict[str, Any],
    snapshot_meta: Dict[str, Any],
    requested_universe_size: int,
    failed_tickers: List[str],
) -> None:
    as_of_dates = sorted({str(value) for value in df["as_of_date"].dropna().tolist()})
    missing_target = [row["ticker"] for _, row in df[df["target_mean_price"].isna()].iterrows()]
    valuation_source_breakdown = {
        str(k): int(v)
        for k, v in df["valuation_source"].value_counts(dropna=False).to_dict().items()
    }
    source_text = "stock-data-hub(API+snapshot) + local DCF valuation link (partial coverage; comps baseline cross-check optional)"
    skip_hub_history = str(os.getenv("IML_SKIP_HUB_PRICE_HISTORY", "0")).strip().lower() in {"1", "true", "yes", "on"}
    if skip_hub_history:
        source_text += " (price_history: snapshot-only, hub online fetch skipped)"
    if _skip_hub_online():
        source_text += " (hub online pull disabled; snapshot-only mode)"

    meta = {
        "generated_at_utc": generated_at,
        "source": source_text,
        "cache_policy": (
            "disabled"
            if not cache_enabled
            else f"enabled; ttl_hours={cache_ttl_hours}; use cached result for non-real-time API calls"
        ),
        "as_of_dates": as_of_dates,
        "universe_size": int(len(df)),
        "requested_universe_size": int(requested_universe_size),
        "coverage_of_requested_universe": (
            float(len(df) / requested_universe_size) if requested_universe_size > 0 else 0.0
        ),
        "failed_ticker_count": int(len(failed_tickers)),
        "failed_tickers": failed_tickers,
        "valuation_source_breakdown": valuation_source_breakdown,
        "skip_hub_price_history": bool(skip_hub_history),
        "skip_hub_online": bool(_skip_hub_online()),
        "dcf_integration": dcf_meta,
        "hub_comps_overlay": hub_comps_meta,
        "local_snapshot": snapshot_meta,
        "calculation": {
            "fair_value_priority": "dcf_iv_base > dcf_external_consensus > targetMeanPrice > close",
            "price_to_fair_value": "close / fair_value; fair_value uses priority above",
            "margin_of_safety": "1 - price_to_fair_value (signed; can be negative when price > fair_value)",
            "upside_to_price": "(fair_value - close) / close = fair_value/close - 1 (common target-price style)",
            "formula_conversion": "upside_to_price = margin_of_safety / (1 - margin_of_safety); margin_of_safety = upside_to_price / (1 + upside_to_price)",
            "quality_score": "percentile(ROE, grossMargins, operatingMargins, debtToEquity inverse) weighted 30/25/25/20",
            "growth_score": "percentile(revenueGrowth, earningsGrowth, earningsQuarterlyGrowth) weighted 35/35/30",
            "momentum_score": "percentile(3m return, 6m return, 12m return, distance to 200D MA) weighted 25/25/30/20",
            "catalyst_score": "percentile(analyst upside, recommendationMean inverse, earningsQuarterlyGrowth, analystCount) weighted 35/25/25/15",
            "risk_score": "percentile(1y volatility, 1y max drawdown, beta, debtToEquity) weighted 35/35/20/10",
            "certainty_score": "weighted(quality_score 45%, risk_control_proxy 35%, analyst_count_percentile 20%)",
            "value_quality_compound_guardrails": "margin_of_safety>=15% and certainty_score>=65 hard gate; margin<30% / certainty<75 soft penalty",
            "dcf_quality_penalty_multiplier": _dcf_quality_penalty_rule_text(),
        },
        "external_mos_references": [
            {
                "source": "Yahoo Finance",
                "reference": "1y Target Est (analyst target); used when DCF iv_base unavailable",
                "url": "https://finance.yahoo.com/quote/AAPL",
            },
            {
                "source": "Local DCF API / dcf_valuation_link",
                "reference": "iv_base used as fair_value for covered symbols",
                "url": "http://127.0.0.1:8000/v1/health",
            },
            {
                "source": "Investopedia",
                "reference": "Margin of Safety = (Current Market Price - Intrinsic Value) / Intrinsic Value",
                "url": "https://www.investopedia.com/terms/m/marginofsafety.asp",
            },
            {
                "source": "Wall Street Prep",
                "reference": "Margin of Safety (%) = (Fair Value - Market Price) / Fair Value",
                "url": "https://www.wallstreetprep.com/knowledge/margin-of-safety/",
            },
            {
                "source": "Morningstar",
                "reference": "Price/Fair Value ratio and discount to fair value = (Fair Value - Price) / Fair Value",
                "url": "https://awgmain.morningstar.com/webhelp/glossary_definitions/mutual_fund/f_3131_Discount_to_Fair_Value.html",
            },
        ],
        "tickers_with_missing_target_mean_price": missing_target,
        "non_realtime_disclaimer": "stock-data-hub 与 DCF API 可能有短延迟；本文件为市场数据支撑，但不是交易所逐笔级实时数据。",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    snapshot_meta = configure_local_snapshot_context(
        snapshot_root=args.snapshot_root,
        snapshot_date=(args.snapshot_date or "").strip() or None,
        enabled=not args.disable_local_snapshot,
    )
    universe = load_universe(args.universe_file)
    ordered_tickers = [(item.get("ticker") or "").strip() for item in universe if item.get("ticker")]

    raw_rows: List[RawMarketRow] = []
    failures: List[str] = []
    cache_hits = 0
    api_fetches = 0
    total = len(universe)
    for idx, item in enumerate(universe, start=1):
        ticker = (item.get("ticker") or "").strip()
        if not ticker:
            continue
        cache_file = _cache_path(args.cache_dir, ticker, args.history_period)
        if not args.no_cache:
            cached = _load_cached_row(
                cache_file=cache_file,
                ttl_hours=args.cache_ttl_hours,
                history_period=args.history_period,
            )
            if cached is not None:
                cached.base_note = item.get("note", "")
                enrich_cached_row_with_backfill(cached)
                raw_rows.append(cached)
                cache_hits += 1
                continue
        try:
            fetched = fetch_raw_market_row_with_retries(
                item,
                history_period=args.history_period,
                timeout_seconds=args.per_ticker_timeout_seconds,
                retries=args.per_ticker_retries,
                timeout_multiplier=args.per_ticker_retry_timeout_multiplier,
                retry_backoff_seconds=args.per_ticker_retry_backoff_seconds,
            )
            raw_rows.append(fetched)
            api_fetches += 1
            if not args.no_cache:
                _save_cached_row(
                    cache_file=cache_file,
                    history_period=args.history_period,
                    row=fetched,
                )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{ticker}: {exc}")

        if idx % 25 == 0 or idx == total:
            print(
                f"[progress] {idx}/{total} "
                f"cache_hits={cache_hits} api_fetches={api_fetches} failures={len(failures)}",
                flush=True,
            )

    if failures and not args.allow_partial:
        raise RuntimeError("Failed to fetch market data:\n" + "\n".join(failures))
    if not raw_rows:
        raise RuntimeError("No valid market rows fetched.")

    dcf_meta = apply_dcf_overlay(
        raw_rows,
        enable_dcf=not args.disable_dcf,
        dcf_link_script=args.dcf_link_script,
        dcf_companies_file=args.dcf_companies_file,
        dcf_base_url=args.dcf_base_url,
        dcf_timeout=args.dcf_timeout,
        dcf_strict=args.dcf_strict,
    )
    hub_comps_meta = apply_hub_comps_overlay(raw_rows)

    scored = build_scored_frame(raw_rows)
    write_real_opportunities(args.output_file, scored, ordered_tickers=ordered_tickers)
    generated_at = datetime.now(timezone.utc).isoformat()
    write_meta(
        args.meta_file,
        scored,
        generated_at=generated_at,
        cache_enabled=not args.no_cache,
        cache_ttl_hours=args.cache_ttl_hours,
        dcf_meta=dcf_meta,
        hub_comps_meta=hub_comps_meta,
        snapshot_meta=snapshot_meta,
        requested_universe_size=len(universe),
        failed_tickers=failures,
    )

    min_date = min(scored["as_of_date"])
    max_date = max(scored["as_of_date"])
    print(f"实时机会池输出: {args.output_file}")
    print(f"元信息输出: {args.meta_file}")
    print(f"样本数: {len(scored)}")
    print(f"行情日期范围: {min_date} ~ {max_date}")
    if args.no_cache:
        print("缓存: disabled")
    else:
        print(
            f"缓存: enabled (ttl={args.cache_ttl_hours}h, cache_hits={cache_hits}, api_fetches={api_fetches})"
        )
    if snapshot_meta.get("enabled"):
        print(
            "本地快照: enabled "
            f"(date={snapshot_meta.get('snapshot_date')}, "
            f"quotes={snapshot_meta.get('quotes_count', 0)}, "
            f"fundamentals={snapshot_meta.get('fundamentals_count', 0)}, "
            f"external={snapshot_meta.get('external_valuations_count', 0)}, "
            f"price_history={snapshot_meta.get('price_history_count', 0)}, "
            f"financial_statements={snapshot_meta.get('financial_statements_count', 0)})"
        )
    else:
        print(f"本地快照: disabled ({snapshot_meta.get('reason', 'manual_disable_or_not_found')})")
    if failures:
        print(f"拉取失败: {len(failures)}")
        if args.allow_partial:
            print("部分成功模式: enabled（失败 ticker 已跳过）")
        for line in failures[:20]:
            print(f"- {line}")
        if len(failures) > 20:
            print(f"... 其余 {len(failures) - 20} 条已写入 meta.failed_tickers")
    print(
        "DCF覆盖: "
        f"{len(dcf_meta.get('covered_tickers', []))}/{len(scored)} "
        f"(coverage={dcf_meta.get('coverage_ratio', 0.0) * 100:.1f}%)"
    )
    print(
        "DCF内生估值覆盖(iv_base): "
        f"{len(dcf_meta.get('covered_iv_tickers', []))}/{len(scored)} "
        f"(coverage={dcf_meta.get('iv_coverage_ratio', 0.0) * 100:.1f}%)"
    )
    source_counts = dcf_meta.get("valuation_source_counts", {})
    print(f"估值来源分布: {source_counts}")
    if hub_comps_meta.get("enabled"):
        print(
            "Hub Comps补充: "
            f"requested={hub_comps_meta.get('request_count', 0)} "
            f"applied={hub_comps_meta.get('applied_count', 0)} "
            f"failed={hub_comps_meta.get('failed_count', 0)} "
            f"status={hub_comps_meta.get('status_counts', {})}"
        )
    if dcf_meta.get("errors"):
        print(f"DCF告警(已自动回退): {dcf_meta.get('errors')}")


if __name__ == "__main__":
    main()
