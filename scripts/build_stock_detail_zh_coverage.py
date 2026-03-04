#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成股票中文详情覆盖率报告")
    parser.add_argument(
        "--stock-profiles",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_profiles.json",
        help="stock_profiles.json",
    )
    parser.add_argument(
        "--tickers-from",
        nargs="+",
        default=[
            str(PROJECT_ROOT / "output" / "top20_methodology_top10_by_group_tiered_real_3markets.csv"),
            str(PROJECT_ROOT / "output" / "top20_first_batch_opportunities_real_3markets.csv"),
            str(PROJECT_ROOT / "output" / "top20_diversified_opportunities_real_3markets.csv"),
        ],
        help="用于抽取待检查 ticker 的 CSV 文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "stock_detail_zh_coverage_real3.json",
        help="输出 JSON",
    )
    return parser.parse_args()


def canonical_ticker(value: str) -> str:
    ticker = (value or "").strip().upper()
    if ticker.endswith(".HK"):
        code = ticker[:-3]
        if code.isdigit():
            ticker = f"{code.zfill(5)}.HK"
    return ticker


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


def load_csv_tickers(path: Path) -> List[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)
        return [canonical_ticker(row.get("ticker", "")) for row in rows if row.get("ticker")]


def main() -> None:
    args = parse_args()
    stock_doc = json.loads(args.stock_profiles.read_text(encoding="utf-8"))
    profiles_raw = stock_doc.get("profiles", {})
    profiles: Dict[str, Dict[str, Any]] = {}
    for key, value in profiles_raw.items():
        k = str(key or "").strip().upper()
        if not k:
            continue
        profiles[k] = value
        profiles[canonical_ticker(k)] = value

    tickers: Set[str] = set()
    for raw in args.tickers_from:
        path = Path(raw)
        for ticker in load_csv_tickers(path):
            if ticker:
                tickers.add(ticker)

    confidence_counter: Counter[str] = Counter()
    summary_counter: Counter[str] = Counter()
    details: List[Dict[str, Any]] = []

    for ticker in sorted(tickers):
        profile = profiles.get(canonical_ticker(ticker))
        if profile is None:
            for key in ticker_variants(ticker):
                if key in profiles:
                    profile = profiles[key]
                    break

        if not profile:
            summary_counter["missing_profile"] += 1
            details.append(
                {
                    "ticker": ticker,
                    "status": "missing_profile",
                    "missing_fields": ["profile"],
                }
            )
            continue

        breakdown = profile.get("product_revenue_breakdown") or []
        has_business = bool(str(profile.get("business_intro_zh") or profile.get("business_intro") or "").strip())
        has_breakdown = isinstance(breakdown, list) and len(breakdown) > 0
        has_customers = bool(str(profile.get("key_customers_zh") or "").strip())
        has_moat = bool(str(profile.get("core_competitiveness_zh") or "").strip())
        has_sources = bool(profile.get("intro_sources"))
        confidence = str(profile.get("intro_data_confidence") or "unknown")

        missing_fields: List[str] = []
        if not has_business:
            missing_fields.append("business_intro_zh")
        if not has_breakdown:
            missing_fields.append("product_revenue_breakdown")
        if not has_customers:
            missing_fields.append("key_customers_zh")
        if not has_moat:
            missing_fields.append("core_competitiveness_zh")
        if not has_sources:
            missing_fields.append("intro_sources")

        if not missing_fields:
            summary_counter["fully_structured"] += 1
        else:
            summary_counter["partially_structured"] += 1

        if "estimated" in confidence:
            summary_counter["estimated_confidence"] += 1
        if confidence.endswith("disclosed"):
            summary_counter["disclosed_confidence"] += 1

        confidence_counter[confidence] += 1
        details.append(
            {
                "ticker": ticker,
                "status": "ok" if not missing_fields else "partial",
                "confidence": confidence,
                "missing_fields": missing_fields,
                "breakdown_items": len(breakdown) if isinstance(breakdown, list) else 0,
            }
        )

    total = len(tickers)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "real3_clickable_tickers",
        "total_tickers": total,
        "summary": dict(summary_counter),
        "confidence_distribution": dict(confidence_counter),
        "fully_structured_ratio": round(summary_counter.get("fully_structured", 0) / total, 4) if total else None,
        "tickers": details,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {args.output}")
    print(f"total={total}, fully_structured={summary_counter.get('fully_structured', 0)}")


if __name__ == "__main__":
    main()
