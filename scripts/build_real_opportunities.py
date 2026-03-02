#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DCF_LINK_SCRIPT = Path(
    "/home/afu/.codex/skills/dcf-valuation-link/scripts/dcf_valuation_link.py"
)
DEFAULT_DCF_COMPANIES_FILE = Path("/home/afu/codex-project/data/companies.json")

YF_TICKER_MAP = {
    "BRK.B": "BRK-B",
}


@dataclass
class DCFValuation:
    symbol: str
    iv_base: float
    price: float | None
    mos_base: float | None
    status: str | None
    pulled_at: str | None


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
    base_note: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建实时数据版机会池输入（Yahoo Finance）")
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.universe_3markets.csv",
        help="股票池输入文件（至少需要 ticker/name/note）",
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
        default=PROJECT_ROOT / "data" / "cache" / "yfinance",
        help="API 缓存目录（默认 data/cache/yfinance）",
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


def _run_dcf_link(args: List[str]) -> Dict[str, Any]:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
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
    if not symbol or not isinstance(valuation, dict):
        return None
    iv_base = _safe_float(valuation.get("iv_base"))
    if iv_base is None or iv_base <= 0:
        return None
    return DCFValuation(
        symbol=symbol,
        iv_base=iv_base,
        price=_safe_float(valuation.get("price")),
        mos_base=_safe_float(valuation.get("mos_base")),
        status=str(valuation.get("status", "")).strip() or None,
        pulled_at=str(payload.get("pulled_at", "")).strip() or None,
    )


def _pull_dcf_portfolio(
    dcf_link_script: Path,
    dcf_base_url: str,
    dcf_timeout: float,
    symbols: List[str],
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
    payload = _run_dcf_link(cmd)
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
            payload = _run_dcf_link(cmd)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{symbol}: {exc}")
            continue
        parsed = _parse_dcf_company_payload(payload)
        if parsed is None:
            failures.append(f"{symbol}: missing/invalid iv_base")
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
    pulled_valuations: Dict[str, DCFValuation] = {}

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
                    )
                else:
                    pulled_valuations, dcf_errors = _pull_dcf_companies_individually(
                        dcf_link_script=dcf_link_script,
                        dcf_base_url=dcf_base_url,
                        dcf_timeout=dcf_timeout,
                        symbols=target_symbols,
                    )
            except Exception as exc:  # noqa: BLE001
                dcf_errors.append(str(exc))
                if dcf_strict:
                    raise

    for row in raw_rows:
        row.dcf_symbol = ticker_to_symbol.get(row.ticker)
        valuation = pulled_valuations.get(row.dcf_symbol or "")
        if enable_dcf and valuation is not None:
            row.fair_value = valuation.iv_base
            row.valuation_source = "dcf_iv_base"
            row.valuation_source_detail = f"{valuation.symbol}:iv_base"
            row.dcf_iv_base = valuation.iv_base
            row.dcf_mos_base = valuation.mos_base
            row.dcf_price = valuation.price
            row.dcf_status = valuation.status
            row.dcf_pulled_at = valuation.pulled_at
            covered_tickers.append(row.ticker)
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

    source_counts: Dict[str, int] = {}
    for row in raw_rows:
        source_counts[row.valuation_source] = source_counts.get(row.valuation_source, 0) + 1

    return {
        "enabled": enable_dcf,
        "dcf_link_script": str(dcf_link_script),
        "dcf_companies_file": str(dcf_companies_file),
        "dcf_base_url": dcf_base_url,
        "available_symbols_count": len(available_symbols or []),
        "requested_symbols": sorted(set(ticker_to_symbol.values())),
        "pulled_symbols": sorted(pulled_valuations.keys()),
        "covered_tickers": sorted(covered_tickers),
        "unresolved_tickers": sorted(unresolved_tickers),
        "errors": dcf_errors,
        "valuation_source_counts": source_counts,
        "coverage_ratio": (len(covered_tickers) / len(raw_rows)) if raw_rows else 0.0,
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
    yf_ticker = YF_TICKER_MAP.get(ticker, ticker)

    ticker_obj = yf.Ticker(yf_ticker)
    info = ticker_obj.info
    history = ticker_obj.history(period=history_period, interval="1d", auto_adjust=True)
    closes = history.get("Close", pd.Series(dtype=float)).dropna()
    if closes.empty:
        raise ValueError(f"{ticker}: missing close history from Yahoo Finance")

    as_of_date = closes.index[-1].date().isoformat()
    close = float(closes.iloc[-1])

    target_mean = _safe_float(info.get("targetMeanPrice"))
    fair_value = target_mean if target_mean and target_mean > 0 else close
    valuation_source = "target_mean_price" if target_mean and target_mean > 0 else "close_fallback"

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
        name=(item.get("name") or info.get("longName") or ticker).strip(),
        sector=(info.get("sector") or item.get("sector") or "Unknown").strip(),
        as_of_date=as_of_date,
        close=close,
        fair_value=fair_value,
        target_mean_price=target_mean,
        return_on_equity=_safe_float(info.get("returnOnEquity")),
        gross_margins=_safe_float(info.get("grossMargins")),
        operating_margins=_safe_float(info.get("operatingMargins")),
        revenue_growth=_safe_float(info.get("revenueGrowth")),
        earnings_growth=_safe_float(info.get("earningsGrowth")),
        earnings_quarterly_growth=_safe_float(info.get("earningsQuarterlyGrowth")),
        debt_to_equity=_safe_float(info.get("debtToEquity")),
        beta=_safe_float(info.get("beta")),
        analyst_count=_safe_float(info.get("numberOfAnalystOpinions")),
        recommendation_mean=_safe_float(info.get("recommendationMean")),
        ret_3m=ret_3m,
        ret_6m=ret_6m,
        ret_12m=ret_12m,
        dist_to_sma200=dist_to_sma200,
        vol_1y=vol_1y,
        max_drawdown_1y=max_drawdown_1y,
        note=note,
        valuation_source=valuation_source,
        valuation_source_detail=(
            "yahoo_target_mean_price" if valuation_source == "target_mean_price" else "close_fallback"
        ),
        base_note=item.get("note", ""),
    )


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
        "quality_score",
        "growth_score",
        "momentum_score",
        "catalyst_score",
        "risk_score",
        "certainty_score",
        "note",
    ]
    row_map = {row["ticker"]: row for _, row in df.iterrows()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for ticker in ordered_tickers:
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
                    "quality_score": f"{float(row['quality_score']):.1f}",
                    "growth_score": f"{float(row['growth_score']):.1f}",
                    "momentum_score": f"{float(row['momentum_score']):.1f}",
                    "catalyst_score": f"{float(row['catalyst_score']):.1f}",
                    "risk_score": f"{float(row['risk_score']):.1f}",
                    "certainty_score": f"{float(row['certainty_score']):.1f}",
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
) -> None:
    as_of_dates = sorted({str(value) for value in df["as_of_date"].dropna().tolist()})
    missing_target = [row["ticker"] for _, row in df[df["target_mean_price"].isna()].iterrows()]
    valuation_source_breakdown = {
        str(k): int(v)
        for k, v in df["valuation_source"].value_counts(dropna=False).to_dict().items()
    }
    meta = {
        "generated_at_utc": generated_at,
        "source": "Yahoo Finance via yfinance + local DCF valuation link (partial coverage)",
        "cache_policy": (
            "disabled"
            if not cache_enabled
            else f"enabled; ttl_hours={cache_ttl_hours}; use cached result for non-real-time API calls"
        ),
        "as_of_dates": as_of_dates,
        "universe_size": int(len(df)),
        "valuation_source_breakdown": valuation_source_breakdown,
        "dcf_integration": dcf_meta,
        "calculation": {
            "fair_value_priority": "dcf_iv_base > targetMeanPrice > close",
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
        "non_realtime_disclaimer": "Yahoo Finance and DCF API may have short delays; this file is market-data-backed but not exchange-tick-level real-time.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    universe = load_universe(args.universe_file)
    ordered_tickers = [(item.get("ticker") or "").strip() for item in universe if item.get("ticker")]

    raw_rows: List[RawMarketRow] = []
    failures: List[str] = []
    cache_hits = 0
    api_fetches = 0
    for item in universe:
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
                raw_rows.append(cached)
                cache_hits += 1
                continue
        try:
            fetched = fetch_raw_market_row(item, history_period=args.history_period)
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

    if failures:
        raise RuntimeError("Failed to fetch market data:\n" + "\n".join(failures))

    dcf_meta = apply_dcf_overlay(
        raw_rows,
        enable_dcf=not args.disable_dcf,
        dcf_link_script=args.dcf_link_script,
        dcf_companies_file=args.dcf_companies_file,
        dcf_base_url=args.dcf_base_url,
        dcf_timeout=args.dcf_timeout,
        dcf_strict=args.dcf_strict,
    )

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
    print(
        "DCF覆盖: "
        f"{len(dcf_meta.get('covered_tickers', []))}/{len(scored)} "
        f"(coverage={dcf_meta.get('coverage_ratio', 0.0) * 100:.1f}%)"
    )
    source_counts = dcf_meta.get("valuation_source_counts", {})
    print(f"估值来源分布: {source_counts}")
    if dcf_meta.get("errors"):
        print(f"DCF告警(已自动回退): {dcf_meta.get('errors')}")


if __name__ == "__main__":
    main()
