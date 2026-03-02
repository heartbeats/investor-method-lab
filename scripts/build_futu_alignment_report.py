#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "investor_profiles.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "futu_alignment_report.json"

DEFAULT_TARGET_STATUSES = {"ready_for_futu_compare", "partial_direct_plus_lookthrough"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成富途对账覆盖报告")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=DEFAULT_INPUT,
        help="输入 investor_profiles.json",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="输出 futu_alignment_report.json",
    )
    parser.add_argument(
        "--investor-ids",
        type=str,
        default="",
        help="手动指定投资人 id，逗号分隔；为空时自动按状态筛选",
    )
    return parser.parse_args()


def _ticker_market(ticker: str) -> str:
    upper = str(ticker or "").strip().upper()
    if upper.endswith(".HK"):
        return "HK"
    if upper.endswith(".SH") or upper.endswith(".SZ") or upper.endswith(".SS"):
        return "CN"
    if re.fullmatch(r"\d{6}", upper):
        return "CN"
    return "US"


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:  # noqa: BLE001
        return None
    return number


def _build_investor_entry(item: Dict[str, Any], market_permissions: Dict[str, str]) -> Dict[str, Any]:
    holdings = item.get("representative_holdings_with_weight") or []
    rows: List[Dict[str, Any]] = []
    market_count: Dict[str, int] = {"US": 0, "HK": 0, "CN": 0, "OTHER": 0}
    market_opend_hits: Dict[str, int] = {"US": 0, "HK": 0, "CN": 0, "OTHER": 0}

    quote_eligible_hits = 0
    any_source_priced_hits = 0
    expected_opend_hits = 0
    actual_opend_hits = 0

    any_source_disclosed_weight_sum = 0.0
    disclosed_weight_sum = 0.0
    opend_disclosed_weight_sum = 0.0

    missing_expected_rows: List[Dict[str, Any]] = []
    permission_blocked_rows: List[Dict[str, Any]] = []

    for row in holdings:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        market = _ticker_market(ticker) if ticker else "OTHER"
        if market not in market_count:
            market = "OTHER"
        market_count[market] += 1

        if ticker:
            quote_eligible_hits += 1

        permission = str(market_permissions.get(market) or "unknown")
        expected_opend = permission == "ok"
        if expected_opend:
            expected_opend_hits += 1
        elif ticker:
            permission_blocked_rows.append(
                {
                    "asset": row.get("asset"),
                    "ticker": ticker or None,
                    "market": market,
                    "permission": permission,
                    "reason": "该市场当前 OpenD 权限非 ok，暂无法要求命中 OpenD。",
                }
            )

        price_source = str(row.get("price_source") or "")
        any_source_priced = bool(price_source)
        if any_source_priced:
            any_source_priced_hits += 1
        opend_hit = price_source == "Futu OpenD"
        if opend_hit:
            market_opend_hits[market] += 1
            actual_opend_hits += 1

        weight_pct = _to_float(row.get("weight_pct"))
        if weight_pct is not None and weight_pct >= 0:
            disclosed_weight_sum += weight_pct
            if any_source_priced:
                any_source_disclosed_weight_sum += weight_pct
            if opend_hit:
                opend_disclosed_weight_sum += weight_pct

        if expected_opend and not opend_hit:
            missing_expected_rows.append(
                {
                    "asset": row.get("asset"),
                    "ticker": ticker or None,
                    "market": market,
                    "price_source": price_source or None,
                    "reason": "该市场 OpenD 权限为 ok，但此持仓未命中 OpenD 报价（代码映射/缓存/源数据问题待排查）",
                }
            )

        rows.append(
            {
                "asset": row.get("asset"),
                "ticker": ticker or None,
                "market": market,
                "weight_pct": weight_pct,
                "price_source": price_source or None,
                "price_text": row.get("price_text"),
                "price_as_of": row.get("price_as_of"),
                "any_source_priced": any_source_priced,
                "expected_opend": expected_opend,
                "opend_hit": opend_hit,
            }
        )

    all_interface_asset_coverage_pct = (
        round(any_source_priced_hits / quote_eligible_hits * 100.0, 2) if quote_eligible_hits > 0 else None
    )
    disclosed_weight_any_source_coverage_pct = (
        round(any_source_disclosed_weight_sum / disclosed_weight_sum * 100.0, 2) if disclosed_weight_sum > 0 else None
    )
    expected_hit_rate_pct = round(actual_opend_hits / expected_opend_hits * 100.0, 2) if expected_opend_hits > 0 else None
    disclosed_weight_opend_coverage_pct = (
        round(opend_disclosed_weight_sum / disclosed_weight_sum * 100.0, 2) if disclosed_weight_sum > 0 else None
    )

    return {
        "id": item.get("id"),
        "name_cn": item.get("name_cn"),
        "name_en": item.get("name_en"),
        "role_type": item.get("role_type"),
        "futu_alignment_status": item.get("futu_alignment_status"),
        "futu_alignment_note": item.get("futu_alignment_note"),
        "holdings_total": len(rows),
        "quote_eligible_hits": quote_eligible_hits,
        "any_source_priced_hits": any_source_priced_hits,
        "all_interface_asset_coverage_pct": all_interface_asset_coverage_pct,
        "market_count": market_count,
        "market_opend_hits": market_opend_hits,
        "any_source_disclosed_weight_sum_pct": round(any_source_disclosed_weight_sum, 2),
        "disclosed_weight_any_source_coverage_pct": disclosed_weight_any_source_coverage_pct,
        "expected_opend_hits": expected_opend_hits,
        "actual_opend_hits": actual_opend_hits,
        "expected_hit_rate_pct": expected_hit_rate_pct,
        "disclosed_weight_sum_pct": round(disclosed_weight_sum, 2),
        "opend_disclosed_weight_sum_pct": round(opend_disclosed_weight_sum, 2),
        "disclosed_weight_opend_coverage_pct": disclosed_weight_opend_coverage_pct,
        "missing_expected_rows": missing_expected_rows,
        "permission_blocked_rows": permission_blocked_rows,
        "rows": rows,
    }


def _select_target_ids(payload: Dict[str, Any], manual_ids: List[str]) -> List[str]:
    if manual_ids:
        return manual_ids
    investors = payload.get("investors") or []
    result: List[str] = []
    for item in investors:
        if not isinstance(item, dict):
            continue
        investor_id = str(item.get("id") or "").strip()
        if not investor_id:
            continue
        status = str(item.get("futu_alignment_status") or "")
        if status in DEFAULT_TARGET_STATUSES:
            result.append(investor_id)
    return result


def build_report(payload: Dict[str, Any], manual_ids: List[str] | None = None) -> Dict[str, Any]:
    investors = payload.get("investors") or []
    by_id = {str(item.get("id") or ""): item for item in investors if isinstance(item, dict)}
    target_ids = _select_target_ids(payload, manual_ids or [])

    futu_runtime = payload.get("futu_alignment_runtime") or {}
    market_permissions = futu_runtime.get("market_permissions") or {}

    focus_entries: List[Dict[str, Any]] = []
    for investor_id in target_ids:
        item = by_id.get(investor_id)
        if not item:
            continue
        focus_entries.append(_build_investor_entry(item, market_permissions=market_permissions))

    total_expected = sum(int(item.get("expected_opend_hits") or 0) for item in focus_entries)
    total_actual = sum(int(item.get("actual_opend_hits") or 0) for item in focus_entries)
    total_holdings = sum(int(item.get("holdings_total") or 0) for item in focus_entries)
    total_quote_eligible_hits = sum(int(item.get("quote_eligible_hits") or 0) for item in focus_entries)
    total_any_source_priced_hits = sum(int(item.get("any_source_priced_hits") or 0) for item in focus_entries)
    total_missing_expected = sum(len(item.get("missing_expected_rows") or []) for item in focus_entries)
    total_permission_blocked_rows = sum(len(item.get("permission_blocked_rows") or []) for item in focus_entries)
    all_interface_asset_coverage_pct = (
        round(total_any_source_priced_hits / total_quote_eligible_hits * 100.0, 2)
        if total_quote_eligible_hits > 0
        else None
    )
    overall_expected_hit_rate_pct = round(total_actual / total_expected * 100.0, 2) if total_expected > 0 else None

    return {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "focus_investor_ids": target_ids,
        "target_selection_mode": "manual_ids" if manual_ids else "auto_by_futu_alignment_status",
        "target_statuses": sorted(DEFAULT_TARGET_STATUSES),
        "futu_runtime_snapshot": {
            "status": futu_runtime.get("status"),
            "endpoint": futu_runtime.get("endpoint"),
            "port": futu_runtime.get("port"),
            "note": futu_runtime.get("note"),
            "market_permissions": market_permissions,
            "market_probe_note": futu_runtime.get("market_probe_note"),
        },
        "summary": {
            "focus_investor_count": len(focus_entries),
            "total_holdings": total_holdings,
            "total_quote_eligible_hits": total_quote_eligible_hits,
            "total_any_source_priced_hits": total_any_source_priced_hits,
            "all_interface_asset_coverage_pct": all_interface_asset_coverage_pct,
            "total_expected_opend_hits": total_expected,
            "total_actual_opend_hits": total_actual,
            "overall_expected_hit_rate_pct": overall_expected_hit_rate_pct,
            "total_missing_expected_rows": total_missing_expected,
            "total_permission_blocked_rows": total_permission_blocked_rows,
        },
        "investors": focus_entries,
        "notes": [
            "主口径为“全接口价格覆盖”（Futu OpenD + Yahoo 等），用于衡量持仓可报价覆盖率。",
            "OpenD 命中字段保留为诊断项（用于定位富途权限/映射问题），不是主可用性指标。",
            "expected_opend 由市场权限推断（US/HK/CN），并不代表该 ticker 一定可交易或一定可拉取。",
            "若 US 权限缺失，US 行不会计入 expected_opend_hits，因此命中率不会被 US 权限问题拉低。",
        ],
    }


def main() -> None:
    args = parse_args()
    payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    manual_ids = [item.strip() for item in args.investor_ids.split(",") if item.strip()]
    report = build_report(payload, manual_ids=manual_ids)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"futu alignment report generated: {args.output_file}")
    print(f"summary: {report['summary']}")


if __name__ == "__main__":
    main()
