#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]

YF_TICKER_MAP = {
    "BRK.B": "BRK-B",
}

TICKER_NAME_CN: Dict[str, str] = {
    "AAPL": "苹果",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "GOOG": "谷歌",
    "AMZN": "亚马逊",
    "META": "Meta",
    "TSLA": "特斯拉",
    "NVDA": "英伟达",
    "BRK.B": "伯克希尔·哈撒韦B",
    "BRK-B": "伯克希尔·哈撒韦B",
    "JPM": "摩根大通",
    "V": "Visa",
    "XOM": "埃克森美孚",
    "UNH": "联合健康",
    "ADBE": "Adobe",
    "0700.HK": "腾讯控股",
    "3690.HK": "美团",
    "9988.HK": "阿里巴巴",
    "1810.HK": "小米集团",
    "1211.HK": "比亚迪股份",
    "9618.HK": "京东集团",
    "9999.HK": "网易",
    "0981.HK": "中芯国际",
    "600519.SS": "贵州茅台",
    "000858.SZ": "五粮液",
    "300750.SZ": "宁德时代",
    "600036.SS": "招商银行",
    "601318.SS": "中国平安",
    "600900.SS": "长江电力",
    "002594.SZ": "比亚迪A",
    "600276.SS": "恒瑞医药",
    "601899.SS": "紫金矿业",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建股票详情页资料（业务介绍/产品介绍/估值）")
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.universe_3markets.csv",
        help="股票池",
    )
    parser.add_argument(
        "--real3-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real_3markets.csv",
        help="实时三市场因子输入",
    )
    parser.add_argument(
        "--real-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real.csv",
        help="实时美股因子输入",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_profiles.json",
        help="输出 JSON",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "cache" / "stock_profiles",
        help="缓存目录",
    )
    parser.add_argument(
        "--cache-ttl-hours",
        type=int,
        default=24,
        help="缓存有效期（小时）",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_valuation_map(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = (row.get("ticker") or "").strip()
        if not ticker:
            continue
        p2fv = safe_float(row.get("price_to_fair_value"))
        quality = safe_float(row.get("quality_score"))
        growth = safe_float(row.get("growth_score"))
        momentum = safe_float(row.get("momentum_score"))
        catalyst = safe_float(row.get("catalyst_score"))
        risk = safe_float(row.get("risk_score"))
        certainty = safe_float(row.get("certainty_score"))
        result[ticker] = {
            "price_to_fair_value": p2fv,
            "margin_of_safety_fv_pct": (1 - p2fv) * 100 if p2fv is not None else None,
            "quality_score": quality,
            "growth_score": growth,
            "momentum_score": momentum,
            "catalyst_score": catalyst,
            "risk_score": risk,
            "certainty_score": certainty,
            "note": row.get("note", ""),
        }
    return result


def cache_path(cache_dir: Path, ticker: str) -> Path:
    key = "".join(ch if ch.isalnum() else "_" for ch in ticker.upper())
    return cache_dir / f"{key}.json"


def load_cache(path: Path, ttl_hours: int) -> Dict[str, Any] | None:
    if ttl_hours <= 0 or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cached_at_raw = payload.get("cached_at_utc")
        profile = payload.get("profile")
        if not cached_at_raw or not isinstance(profile, dict):
            return None
        cached_at = datetime.fromisoformat(str(cached_at_raw))
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
            return None
        return profile
    except Exception:  # noqa: BLE001
        return None


def save_cache(path: Path, profile: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_products(summary: str) -> str:
    text = (summary or "").strip()
    if not text:
        return "公开资料暂无结构化产品介绍。"
    parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    if not parts:
        return "公开资料暂无结构化产品介绍。"
    return "；".join(parts[:2])


def to_yf_ticker(ticker: str) -> str:
    base = (ticker or "").strip().upper()
    if not base:
        return base
    mapped = YF_TICKER_MAP.get(base, base)
    if mapped.endswith(".HK"):
        code = mapped[:-3]
        if code.isdigit():
            # Yahoo 常用 4 位港股代码：00881.HK -> 0881.HK
            mapped = f"{str(int(code)).zfill(4)}.HK"
    return mapped


def fetch_stock_profile(ticker: str) -> Dict[str, Any] | None:
    yf_ticker = to_yf_ticker(ticker)
    ticker_obj = yf.Ticker(yf_ticker)
    history = ticker_obj.history(period="5d", interval="1d", auto_adjust=False)
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return None
    closes = closes.dropna()
    price = float(closes.iloc[-1])
    as_of_date = closes.index[-1].date().isoformat()

    info = ticker_obj.info if isinstance(ticker_obj.info, dict) else {}
    name = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency") or "USD"
    business_summary = info.get("longBusinessSummary") or ""

    return {
        "ticker": ticker,
        "yf_ticker": yf_ticker,
        "name": name,
        "name_cn": TICKER_NAME_CN.get(ticker) or TICKER_NAME_CN.get(yf_ticker),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "business_intro": business_summary or "暂无公开业务介绍。",
        "products_intro": summarize_products(business_summary),
        "current_price": round(price, 4),
        "currency": currency,
        "price_as_of": as_of_date,
        "target_mean_price": safe_float(info.get("targetMeanPrice")),
        "trailing_pe": safe_float(info.get("trailingPE")),
        "forward_pe": safe_float(info.get("forwardPE")),
        "price_to_book": safe_float(info.get("priceToBook")),
        "enterprise_to_ebitda": safe_float(info.get("enterpriseToEbitda")),
        "market_cap": safe_float(info.get("marketCap")),
        "source": "Yahoo Finance via yfinance",
    }


def main() -> None:
    args = parse_args()

    universe_rows = read_csv_rows(args.universe_file)
    real3_rows = read_csv_rows(args.real3_file) if args.real3_file.exists() else []
    real_rows = read_csv_rows(args.real_file) if args.real_file.exists() else []

    tickers = []
    for row in universe_rows:
        ticker = (row.get("ticker") or "").strip()
        if ticker:
            tickers.append(ticker)
    for row in real3_rows + real_rows:
        ticker = (row.get("ticker") or "").strip()
        if ticker:
            tickers.append(ticker)
    tickers = sorted(set(tickers))

    valuation_real3 = build_valuation_map(real3_rows)
    valuation_real = build_valuation_map(real_rows)

    profiles: Dict[str, Dict[str, Any]] = {}
    cache_hits = 0
    api_fetches = 0
    for ticker in tickers:
        cpath = cache_path(args.cache_dir, ticker)
        profile = None
        if not args.no_cache:
            profile = load_cache(cpath, ttl_hours=args.cache_ttl_hours)
            if profile is not None:
                cache_hits += 1

        if profile is None:
            profile = fetch_stock_profile(ticker)
            if profile is None:
                continue
            api_fetches += 1
            if not args.no_cache:
                save_cache(cpath, profile)

        profile["valuation_real3"] = valuation_real3.get(ticker)
        profile["valuation_real"] = valuation_real.get(ticker)
        if not profile.get("name_cn"):
            # 兼容使用 universe 中名称（含中文）
            from_universe = next((x.get("name") for x in universe_rows if x.get("ticker") == ticker), None)
            if from_universe:
                profile["name_cn"] = from_universe
        profiles[ticker] = profile

    payload = {
        "as_of_date": datetime.now(timezone.utc).date().isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_count": len(profiles),
        "profiles": profiles,
        "non_realtime_disclaimer": "行情与估值数据为市场数据口径，存在短延迟，不构成投资建议。",
        "cache_policy": (
            "disabled"
            if args.no_cache
            else f"enabled; ttl_hours={args.cache_ttl_hours}; cache_hits={cache_hits}; api_fetches={api_fetches}"
        ),
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"股票资料库已生成: {args.output_file}")
    print(f"股票数: {len(profiles)}")
    if args.no_cache:
        print("缓存: disabled")
    else:
        print(f"缓存: enabled (ttl={args.cache_ttl_hours}h, cache_hits={cache_hits}, api_fetches={api_fetches})")


if __name__ == "__main__":
    main()
