#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将中文公司与产品结构化资料合并到 stock_profiles.json")
    parser.add_argument(
        "--stock-profiles",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_profiles.json",
        help="股票资料库 JSON",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_detail_zh_overrides.json",
        help="中文覆盖数据 JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "stock_profiles.json",
        help="输出 JSON（默认覆盖 stock_profiles.json）",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    if "." in ticker and not ticker.endswith((".HK", ".SS", ".SZ")):
        variants.append(ticker.replace(".", "-"))
    if "-" in ticker:
        variants.append(ticker.replace("-", "."))
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


def main() -> None:
    args = parse_args()
    stock_doc = load_json(args.stock_profiles)
    override_doc = load_json(args.overrides)

    profiles = stock_doc.get("profiles", {})
    override_profiles = override_doc.get("profiles", {})

    applied = 0
    missing: List[str] = []
    for raw_ticker, payload in override_profiles.items():
        variants = ticker_variants(raw_ticker)
        matched_key = None
        for key in variants:
            if key in profiles:
                matched_key = key
                break
        profile = profiles.get(matched_key) if matched_key else None
        if not profile:
            matched_key = variants[0] if variants else (raw_ticker or '').strip().upper()
            profile = {
                "ticker": matched_key,
                "yf_ticker": matched_key,
                "name": str(payload.get("name_cn") or payload.get("name") or matched_key).strip(),
            }
            profiles[matched_key] = profile

        fiscal_period = str(payload.get("fiscal_period") or "未披露")
        data_confidence = str(payload.get("data_confidence") or "unknown")
        business_intro_zh = str(payload.get("business_intro_zh") or "").strip()
        how_it_makes_money_zh = str(payload.get("how_it_makes_money_zh") or "").strip()
        problem_solved_zh = str(payload.get("problem_solved_zh") or "").strip()
        payers_zh = str(payload.get("payers_zh") or "").strip()
        users_zh = str(payload.get("users_zh") or "").strip()
        products = payload.get("product_revenue_breakdown") or []
        key_customers = str(payload.get("key_customers_zh") or "").strip()
        competitiveness = str(payload.get("core_competitiveness_zh") or "").strip()
        revenue_share_note = str(payload.get("revenue_share_note_zh") or "").strip()
        sources = payload.get("sources") or []

        direct_products_intro_zh = str(payload.get("products_intro_zh") or "").strip()
        products_intro_zh = direct_products_intro_zh or build_products_intro_text(
            fiscal_period=fiscal_period,
            revenue_share_note=revenue_share_note,
            products=products,
            key_customers=key_customers,
            competitiveness=competitiveness,
        )

        existing_business_intro = str(profile.get("business_intro") or "").strip()
        existing_products_intro = str(profile.get("products_intro") or "").strip()
        business_intro_raw = str(profile.get("business_intro_raw") or "").strip()
        products_intro_raw = str(profile.get("products_intro_raw") or "").strip()

        if existing_business_intro and existing_business_intro != business_intro_zh and not business_intro_raw:
            business_intro_raw = existing_business_intro
        if existing_products_intro and existing_products_intro != products_intro_zh and not products_intro_raw:
            products_intro_raw = existing_products_intro

        profile["business_intro_zh"] = business_intro_zh
        if business_intro_raw:
            profile["business_intro_raw"] = business_intro_raw
            profile["business_intro"] = business_intro_raw
        elif not existing_business_intro:
            profile["business_intro"] = business_intro_zh

        profile["how_it_makes_money_zh"] = how_it_makes_money_zh
        profile["problem_solved_zh"] = problem_solved_zh
        profile["payers_zh"] = payers_zh
        profile["users_zh"] = users_zh
        profile["product_revenue_breakdown"] = products
        profile["key_customers_zh"] = key_customers
        profile["core_competitiveness_zh"] = competitiveness
        profile["revenue_share_note_zh"] = revenue_share_note
        profile["intro_fiscal_period"] = fiscal_period
        profile["intro_data_confidence"] = data_confidence
        profile["intro_sources"] = sources
        profile["products_intro_zh"] = products_intro_zh
        if products_intro_raw:
            profile["products_intro_raw"] = products_intro_raw
            profile["products_intro"] = products_intro_raw
        elif not existing_products_intro:
            profile["products_intro"] = products_intro_zh
        applied += 1

    stock_doc["profiles"] = profiles
    stock_doc["profile_count"] = len(profiles)
    stock_doc["zh_detail_overrides_meta"] = {
        "applied": applied,
        "missing_tickers": missing,
        "override_count": len(override_profiles),
        "applied_at_utc": datetime.now(timezone.utc).isoformat(),
        "override_file": str(args.overrides),
    }

    args.output.write_text(json.dumps(stock_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已更新: {args.output}")
    print(f"应用覆盖: {applied}/{len(override_profiles)}")
    if missing:
        print(f"未命中 ticker: {', '.join(missing)}")


if __name__ == "__main__":
    main()
