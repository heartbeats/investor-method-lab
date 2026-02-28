#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]

YF_TICKER_MAP = {
    "BRK.B": "BRK-B",
}


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
    price_upside = (fair_value / close - 1.0) if close > 0 else 0.0

    ret_3m = _calc_return(closes, 63)
    ret_6m = _calc_return(closes, 126)
    ret_12m = _calc_return(closes, 252)

    sma200 = float(closes.tail(200).mean()) if len(closes) >= 30 else float(closes.mean())
    dist_to_sma200 = (close / sma200 - 1.0) if sma200 else None

    returns = closes.pct_change().dropna().tail(252)
    vol_1y = float(returns.std() * math.sqrt(252)) if not returns.empty else None
    max_drawdown_1y = _calc_max_drawdown(closes.tail(252))

    note_parts = [item.get("note", "").strip()]
    note_parts.append(f"real-data@{as_of_date}")
    note_parts.append(f"close={close:.2f}")
    if target_mean and target_mean > 0:
        note_parts.append(f"target={target_mean:.2f}")
    else:
        note_parts.append("target=NA(fallback-close)")
    note_parts.append(f"upside={price_upside * 100:.1f}%")
    note = " | ".join(part for part in note_parts if part)

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


def write_real_opportunities(path: Path, df: pd.DataFrame, ordered_tickers: List[str]) -> None:
    fieldnames = [
        "ticker",
        "name",
        "sector",
        "price_to_fair_value",
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
                    "price_to_fair_value": f"{float(row['price_to_fair_value']):.4f}",
                    "quality_score": f"{float(row['quality_score']):.1f}",
                    "growth_score": f"{float(row['growth_score']):.1f}",
                    "momentum_score": f"{float(row['momentum_score']):.1f}",
                    "catalyst_score": f"{float(row['catalyst_score']):.1f}",
                    "risk_score": f"{float(row['risk_score']):.1f}",
                    "certainty_score": f"{float(row['certainty_score']):.1f}",
                    "note": row["note"],
                }
            )


def write_meta(path: Path, df: pd.DataFrame, generated_at: str) -> None:
    as_of_dates = sorted({str(value) for value in df["as_of_date"].dropna().tolist()})
    missing_target = [row["ticker"] for _, row in df[df["target_mean_price"].isna()].iterrows()]
    meta = {
        "generated_at_utc": generated_at,
        "source": "Yahoo Finance via yfinance",
        "as_of_dates": as_of_dates,
        "universe_size": int(len(df)),
        "calculation": {
            "price_to_fair_value": "close / fair_value; fair_value = targetMeanPrice, fallback=close",
            "quality_score": "percentile(ROE, grossMargins, operatingMargins, debtToEquity inverse) weighted 30/25/25/20",
            "growth_score": "percentile(revenueGrowth, earningsGrowth, earningsQuarterlyGrowth) weighted 35/35/30",
            "momentum_score": "percentile(3m return, 6m return, 12m return, distance to 200D MA) weighted 25/25/30/20",
            "catalyst_score": "percentile(analyst upside, recommendationMean inverse, earningsQuarterlyGrowth, analystCount) weighted 35/25/25/15",
            "risk_score": "percentile(1y volatility, 1y max drawdown, beta, debtToEquity) weighted 35/35/20/10",
            "certainty_score": "weighted(quality_score 45%, risk_control_proxy 35%, analyst_count_percentile 20%)",
            "value_quality_compound_guardrails": "margin_of_safety>=15% and certainty_score>=65 hard gate; margin<30% / certainty<75 soft penalty",
        },
        "tickers_with_missing_target_mean_price": missing_target,
        "non_realtime_disclaimer": "Yahoo Finance data may have short delays; this file is market-data-backed but not exchange-tick-level real-time.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    universe = load_universe(args.universe_file)
    ordered_tickers = [(item.get("ticker") or "").strip() for item in universe if item.get("ticker")]

    raw_rows: List[RawMarketRow] = []
    failures: List[str] = []
    for item in universe:
        ticker = (item.get("ticker") or "").strip()
        if not ticker:
            continue
        try:
            raw_rows.append(fetch_raw_market_row(item, history_period=args.history_period))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{ticker}: {exc}")

    if failures:
        raise RuntimeError("Failed to fetch market data:\n" + "\n".join(failures))

    scored = build_scored_frame(raw_rows)
    write_real_opportunities(args.output_file, scored, ordered_tickers=ordered_tickers)
    generated_at = datetime.now(timezone.utc).isoformat()
    write_meta(args.meta_file, scored, generated_at=generated_at)

    min_date = min(scored["as_of_date"])
    max_date = max(scored["as_of_date"])
    print(f"实时机会池输出: {args.output_file}")
    print(f"元信息输出: {args.meta_file}")
    print(f"样本数: {len(scored)}")
    print(f"行情日期范围: {min_date} ~ {max_date}")


if __name__ == "__main__":
    main()
