#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import signal
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
    parser.add_argument(
        "--per-ticker-timeout-seconds",
        type=int,
        default=12,
        help="单只股票抓取超时秒数（<=0 表示不超时）",
    )
    parser.add_argument(
        "--zh-overrides-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_detail_zh_overrides.json",
        help="中文公司与产品结构化覆盖文件",
    )
    parser.add_argument(
        "--disable-zh-overrides",
        action="store_true",
        help="禁用中文覆盖合并",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
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


def ticker_variants(value: str) -> List[str]:
    ticker = (value or "").strip().upper()
    if not ticker:
        return []
    variants = [ticker]
    if ticker.endswith(".HK"):
        code = ticker[:-3]
        if code.isdigit():
            variants.append(f"{code.zfill(5)}.HK")
            variants.append(f"{int(code)}.HK")
    dedup: List[str] = []
    seen = set()
    for item in variants:
        if item not in seen:
            dedup.append(item)
            seen.add(item)
    return dedup


def build_products_intro_text(
    fiscal_period: str,
    revenue_share_note: str,
    products: List[Dict[str, Any]],
    key_customers: str,
    competitiveness: str,
) -> str:
    lines = [f"披露期：{fiscal_period}", "产品与收入结构："]
    for idx, item in enumerate(products, start=1):
        product = item.get("product", "未披露产品")
        share = item.get("revenue_share", "未披露")
        customers = item.get("customers", "未披露")
        moat = item.get("core_competitiveness", "未披露")
        lines.append(f"{idx}. {product}｜收入占比：{share}｜客户：{customers}｜竞争力：{moat}")
    if key_customers:
        lines.append(f"公司主要客户：{key_customers}")
    if competitiveness:
        lines.append(f"公司核心竞争力：{competitiveness}")
    if revenue_share_note:
        lines.append(f"口径说明：{revenue_share_note}")
    return "\n".join(lines)


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_json_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def apply_zh_overrides(
    profiles: Dict[str, Dict[str, Any]],
    overrides_file: Path,
) -> Dict[str, Any]:
    if not overrides_file.exists():
        return {
            "applied": 0,
            "override_count": 0,
            "missing_tickers": [],
            "override_file": str(overrides_file),
        }

    payload = json.loads(overrides_file.read_text(encoding="utf-8"))
    overrides = payload.get("profiles", {})
    applied = 0
    missing: List[str] = []
    for raw_ticker, item in overrides.items():
        matched_key = None
        for key in ticker_variants(raw_ticker):
            if key in profiles:
                matched_key = key
                break
        profile = profiles.get(matched_key) if matched_key else None
        if not profile:
            missing.append((raw_ticker or "").strip().upper())
            continue

        fiscal_period = str(item.get("fiscal_period") or "未披露")
        data_confidence = str(item.get("data_confidence") or "unknown")
        business_intro_zh = str(item.get("business_intro_zh") or "").strip()
        products = item.get("product_revenue_breakdown") or []
        key_customers = str(item.get("key_customers_zh") or "").strip()
        competitiveness = str(item.get("core_competitiveness_zh") or "").strip()
        revenue_share_note = str(item.get("revenue_share_note_zh") or "").strip()
        sources = item.get("sources") or []

        profile["business_intro_zh"] = business_intro_zh
        if business_intro_zh:
            profile["business_intro"] = business_intro_zh
        profile["product_revenue_breakdown"] = products
        profile["key_customers_zh"] = key_customers
        profile["core_competitiveness_zh"] = competitiveness
        profile["revenue_share_note_zh"] = revenue_share_note
        profile["intro_fiscal_period"] = fiscal_period
        profile["intro_data_confidence"] = data_confidence
        profile["intro_sources"] = sources
        profile["products_intro_zh"] = build_products_intro_text(
            fiscal_period=fiscal_period,
            revenue_share_note=revenue_share_note,
            products=products,
            key_customers=key_customers,
            competitiveness=competitiveness,
        )
        profile["products_intro"] = profile["products_intro_zh"]
        applied += 1

    return {
        "applied": applied,
        "override_count": len(overrides),
        "missing_tickers": missing,
        "override_file": str(overrides_file),
    }


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


class StockFetchTimeout(Exception):
    pass


def _timeout_handler(_signum: int, _frame: Any) -> None:
    raise StockFetchTimeout


def fetch_stock_profile_with_timeout(ticker: str, timeout_seconds: int) -> Dict[str, Any] | None:
    if timeout_seconds <= 0:
        try:
            return fetch_stock_profile(ticker)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 抓取失败 {ticker}: {exc}")
            return None

    old_handler = signal.getsignal(signal.SIGALRM)
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_seconds)
        return fetch_stock_profile(ticker)
    except StockFetchTimeout:
        print(f"[WARN] 超时跳过 {ticker}: {timeout_seconds}s")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] 抓取失败 {ticker}: {exc}")
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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
    universe_name_map = {row.get("ticker", ""): row.get("name", "") for row in universe_rows if row.get("ticker")}

    valuation_real3 = build_valuation_map(real3_rows)
    valuation_real = build_valuation_map(real_rows)

    profiles: Dict[str, Dict[str, Any]] = {}
    cache_hits = 0
    api_fetches = 0
    failed_tickers: List[str] = []
    for ticker in tickers:
        cpath = cache_path(args.cache_dir, ticker)
        profile = None
        if not args.no_cache:
            profile = load_cache(cpath, ttl_hours=args.cache_ttl_hours)
            if profile is not None:
                cache_hits += 1

        if profile is None:
            profile = fetch_stock_profile_with_timeout(ticker, args.per_ticker_timeout_seconds)
            if profile is None:
                failed_tickers.append(ticker)
                continue
            api_fetches += 1
            if not args.no_cache:
                save_cache(cpath, profile)

        profile["valuation_real3"] = valuation_real3.get(ticker)
        profile["valuation_real"] = valuation_real.get(ticker)
        if not profile.get("name_cn"):
            # 兼容使用 universe 中名称（含中文）
            from_universe = universe_name_map.get(ticker)
            if from_universe:
                profile["name_cn"] = from_universe
        profiles[ticker] = sanitize_json_value(profile)

    zh_meta: Dict[str, Any] | None = None
    if not args.disable_zh_overrides:
        zh_meta = apply_zh_overrides(
            profiles=profiles,
            overrides_file=args.zh_overrides_file,
        )

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
    if zh_meta is not None:
        payload["zh_detail_overrides_meta"] = zh_meta

    payload = sanitize_json_value(payload)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    print(f"股票资料库已生成: {args.output_file}")
    print(f"股票数: {len(profiles)}")
    if args.no_cache:
        print("缓存: disabled")
    else:
        print(f"缓存: enabled (ttl={args.cache_ttl_hours}h, cache_hits={cache_hits}, api_fetches={api_fetches})")
    print(f"失败数: {len(failed_tickers)}")
    if failed_tickers:
        print(f"失败ticker: {', '.join(failed_tickers[:30])}{' ...' if len(failed_tickers) > 30 else ''}")
    if zh_meta is not None:
        print(
            f"中文覆盖: {zh_meta.get('applied', 0)}/{zh_meta.get('override_count', 0)} "
            f"(missing={len(zh_meta.get('missing_tickers', []))})"
        )


if __name__ == "__main__":
    main()
