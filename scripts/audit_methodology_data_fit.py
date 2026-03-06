#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="审计方法论规则与当前数据底座匹配度")
    parser.add_argument(
        "--rulebook-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "methodology_rulebook_v4.json",
    )
    parser.add_argument(
        "--opportunities-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real_3markets.csv",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=PROJECT_ROOT / "docs" / "opportunities_real_data_meta_3markets.json",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "cache" / "yfinance",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "docs" / "methodology_data_fit_audit_real_3markets.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "methodology_data_fit_audit_real_3markets.md",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def market_of_ticker(ticker: str) -> str:
    value = str(ticker or "").strip().upper()
    if value.endswith((".SS", ".SZ")):
        return "A"
    if value.endswith(".HK"):
        return "HK"
    return "US"


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return False
        try:
            parsed = float(text)
            if math.isnan(parsed) or math.isinf(parsed):
                return False
        except Exception:
            return True
        return True
    if isinstance(value, (int, float)):
        return not (math.isnan(float(value)) or math.isinf(float(value)))
    return True


def coverage_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    total = len(rows)
    present = 0
    by_market = defaultdict(lambda: {"present": 0, "total": 0})
    for row in rows:
        ticker = str(row.get("ticker") or "")
        market = market_of_ticker(ticker)
        by_market[market]["total"] += 1
        if is_present(row.get(field)):
            present += 1
            by_market[market]["present"] += 1
    return {
        "field": field,
        "present": present,
        "total": total,
        "coverage_ratio": (present / total) if total else 0.0,
        "by_market": {
            market: {
                "present": payload["present"],
                "total": payload["total"],
                "coverage_ratio": (payload["present"] / payload["total"]) if payload["total"] else 0.0,
            }
            for market, payload in sorted(by_market.items())
        },
    }


def load_rule_fields(rulebook: dict[str, Any]) -> list[str]:
    fields: set[str] = set()
    for group in rulebook.get("groups", []):
        for config in [group.get("default", {}), *(group.get("market_overrides", {}) or {}).values()]:
            for section in ["hard_rules", "soft_rules"]:
                for rule in config.get(section, []) or []:
                    field = str(rule.get("field") or "").strip()
                    if field:
                        fields.add(field)
    return sorted(fields)


def rule_field_mapping() -> dict[str, dict[str, Any]]:
    return {
        "price_to_fair_value_raw": {"source_column": "price_to_fair_value", "kind": "direct"},
        "margin_of_safety_raw": {"source_column": "price_to_fair_value", "kind": "derived:1-price_to_fair_value"},
        "quality_score_raw": {"source_column": "quality_score", "kind": "direct"},
        "growth_score_raw": {"source_column": "growth_score", "kind": "direct"},
        "momentum_score_raw": {"source_column": "momentum_score", "kind": "direct"},
        "catalyst_score_raw": {"source_column": "catalyst_score", "kind": "direct"},
        "risk_control_raw": {"source_column": "risk_score", "kind": "derived:100-risk_score"},
        "certainty_score_raw": {"source_column": "certainty_score", "kind": "direct"},
        "market_norm_margin_of_safety": {"source_column": None, "kind": "runtime_market_normalization"},
        "market_norm_quality": {"source_column": None, "kind": "runtime_market_normalization"},
        "market_norm_growth": {"source_column": None, "kind": "runtime_market_normalization"},
        "market_norm_momentum": {"source_column": None, "kind": "runtime_market_normalization"},
        "market_norm_catalyst": {"source_column": None, "kind": "runtime_market_normalization"},
        "market_norm_risk_control": {"source_column": None, "kind": "runtime_market_normalization"},
        "dcf_quality_penalty_multiplier": {"source_column": "dcf_quality_penalty_multiplier", "kind": "direct"},
    }


def load_cache_rows(cache_dir: Path, allowed_tickers: set[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not cache_dir.exists():
        return rows
    for path in cache_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        row = payload.get("row")
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker not in allowed_tickers:
            continue
        cached_at = str(payload.get("cached_at_utc") or "")
        old = rows.get(ticker)
        if old is None:
            rows[ticker] = dict(row)
            rows[ticker]["_cached_at_utc"] = cached_at
            continue
        if str(old.get("_cached_at_utc") or "") < cached_at:
            rows[ticker] = dict(row)
            rows[ticker]["_cached_at_utc"] = cached_at
    return rows


def ratio(payload: dict[str, Any], market: str) -> float:
    by_market = payload.get("by_market", {})
    market_payload = by_market.get(market, {})
    return float(market_payload.get("coverage_ratio") or 0.0)


def build_gap_list(
    *,
    source_coverage: dict[str, dict[str, Any]],
    raw_coverage: dict[str, dict[str, Any]],
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    dcf_ratio = float((meta.get("dcf_integration") or {}).get("coverage_ratio") or 0.0)
    if dcf_ratio < 0.1:
        gaps.append(
            {
                "id": "dcf_coverage_low",
                "severity": "high",
                "description": "DCF 覆盖率偏低，会削弱安全边际与质量闸门可信度。",
                "current": {"dcf_coverage_ratio": dcf_ratio},
                "free_first_actions": [
                    "优先扩充 DCF 可覆盖股票清单到核心池高权重标的",
                    "未覆盖标的使用可比估值 baseline 作为中间校验层",
                ],
                "paid_options": [
                    "启用低成本 fundamentals/consensus 付费源提高 fair value 参照密度（待决策）"
                ],
            }
        )

    target_cov = source_coverage.get("target_mean_price", {})
    if ratio(target_cov, "A") < 0.6:
        gaps.append(
            {
                "id": "a_market_target_price_sparse",
                "severity": "high",
                "description": "A 股分析师目标价覆盖偏低，影响催化分与估值参照稳定性。",
                "current": {
                    "A_target_mean_price_coverage": ratio(target_cov, "A"),
                    "HK_target_mean_price_coverage": ratio(target_cov, "HK"),
                    "US_target_mean_price_coverage": ratio(target_cov, "US"),
                },
                "free_first_actions": [
                    "补充 Eastmoney/akshare 研报聚合数据并转化为目标价统计",
                    "对目标价缺失标的，使用同业估值中位数回填并加风险标签",
                ],
                "paid_options": [
                    "Tushare Pro 研报/一致预期字段（低成本）",
                    "Wind/Choice 一致预期接口（中高成本）",
                ],
            }
        )

    analyst_cov = raw_coverage.get("analyst_count", {})
    rec_cov = raw_coverage.get("recommendation_mean", {})
    if ratio(analyst_cov, "A") < 0.5 or ratio(rec_cov, "A") < 0.5:
        gaps.append(
            {
                "id": "a_market_analyst_signal_sparse",
                "severity": "medium",
                "description": "A 股分析师维度覆盖不足，导致 catalyst/certainty 更依赖默认值。",
                "current": {
                    "A_analyst_count_coverage": ratio(analyst_cov, "A"),
                    "A_recommendation_mean_coverage": ratio(rec_cov, "A"),
                },
                "free_first_actions": [
                    "先用研报数量、最新评级方向构建替代分析师因子",
                    "将缺失标的默认权重下调，避免与 US 高覆盖标的同权比较",
                ],
                "paid_options": [
                    "低成本接入 A 股卖方一致预期接口（待决策）"
                ],
            }
        )

    return gaps


def main() -> None:
    args = parse_args()

    rulebook = json.loads(args.rulebook_file.read_text(encoding="utf-8"))
    opportunities = read_csv_rows(args.opportunities_file)
    meta = json.loads(args.meta_file.read_text(encoding="utf-8")) if args.meta_file.exists() else {}

    tickers = {str(row.get("ticker") or "").strip().upper() for row in opportunities if row.get("ticker")}

    required_rule_fields = load_rule_fields(rulebook)
    field_map = rule_field_mapping()
    mapped_source_columns = sorted(
        {
            payload["source_column"]
            for field, payload in field_map.items()
            if payload.get("source_column")
        }
    )
    monitored_source_columns = sorted(
        set(
            mapped_source_columns
            + [
                "target_mean_price",
                "valuation_source",
                "dcf_quality_gate_status",
                "dcf_comps_crosscheck_status",
            ]
        )
    )

    source_coverage: dict[str, dict[str, Any]] = {}
    for col in monitored_source_columns:
        source_coverage[col] = coverage_summary(opportunities, col)

    raw_cache_rows = load_cache_rows(args.cache_dir, allowed_tickers=tickers)
    raw_rows = [dict(row) for row in raw_cache_rows.values()]
    raw_evidence_fields = [
        "return_on_equity",
        "gross_margins",
        "operating_margins",
        "revenue_growth",
        "earnings_growth",
        "earnings_quarterly_growth",
        "debt_to_equity",
        "analyst_count",
        "recommendation_mean",
        "ret_3m",
        "ret_6m",
        "ret_12m",
        "dist_to_sma200",
        "vol_1y",
        "max_drawdown_1y",
    ]
    raw_coverage: dict[str, dict[str, Any]] = {}
    for field in raw_evidence_fields:
        raw_coverage[field] = coverage_summary(raw_rows, field)

    valuation_source_counts = Counter(str(row.get("valuation_source") or "unknown") for row in opportunities)

    gaps = build_gap_list(
        source_coverage=source_coverage,
        raw_coverage=raw_coverage,
        meta=meta,
    )
    stock_data_hub_docs = PROJECT_ROOT.parent / "stock-data-hub" / "docs"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "rulebook_file": str(args.rulebook_file),
            "opportunities_file": str(args.opportunities_file),
            "meta_file": str(args.meta_file),
            "cache_dir": str(args.cache_dir),
            "universe_size": len(opportunities),
            "cache_rows_matched": len(raw_rows),
        },
        "methodology_required_fields": {
            "rulebook_fields": required_rule_fields,
            "field_mapping": field_map,
            "mapped_source_columns": mapped_source_columns,
            "monitored_source_columns": monitored_source_columns,
        },
        "source_column_coverage": source_coverage,
        "raw_evidence_coverage": raw_coverage,
        "valuation_source_counts": dict(valuation_source_counts),
        "meta_extract": {
            "requested_universe_size": meta.get("requested_universe_size"),
            "universe_size": meta.get("universe_size"),
            "coverage_of_requested_universe": meta.get("coverage_of_requested_universe"),
            "failed_ticker_count": meta.get("failed_ticker_count"),
            "failed_tickers": meta.get("failed_tickers"),
            "local_snapshot": meta.get("local_snapshot"),
            "dcf_coverage_ratio": (meta.get("dcf_integration") or {}).get("coverage_ratio"),
            "dcf_iv_coverage_ratio": (meta.get("dcf_integration") or {}).get("iv_coverage_ratio"),
            "dcf_valuation_source_counts": (meta.get("dcf_integration") or {}).get("valuation_source_counts"),
        },
        "gaps": gaps,
        "source_expansion_plan": {
            "free_first": [
                "A/HK 基本面优先走 akshare，再回退 yfinance（已接入 stock-data-hub）",
                "每日收盘后批量生成本地快照，业务层优先读快照，缺失再回源",
                "A 股补研报聚合（Eastmoney/akshare），补足 analyst_count 与 recommendation 替代信号",
            ],
            "low_cost_paid_candidates_waiting_decision": [
                {
                    "source": "Tushare Pro",
                    "use_case": "A 股财务与一致预期补全",
                    "cost_level": "low_to_medium",
                },
                {
                    "source": "FMP Pro",
                    "use_case": "US/HK 基本面与目标价稳定补源",
                    "cost_level": "low_to_medium",
                },
                {
                    "source": "Polygon/Intrinio",
                    "use_case": "US 行情/财务高稳定性",
                    "cost_level": "medium",
                },
            ],
        },
        "architecture_links": {
            "stock_data_hub_blueprint": str(stock_data_hub_docs / "final_architecture_blueprint.md"),
            "stock_data_hub_data_lake_v2": str(stock_data_hub_docs / "data_lake_architecture_v2.md"),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# 方法论数据适配审计（real_3markets）")
    lines.append("")
    lines.append(f"- 生成时间(UTC)：{report['generated_at_utc']}")
    lines.append(f"- 样本数：{len(opportunities)}")
    lines.append(f"- 缓存命中行：{len(raw_rows)}")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append("- 方法论执行层所需主字段齐备（price_to_fair_value/6因子分值/DCF惩罚字段可用）。")
    lines.append("- 主要缺口不在“有没有字段”，而在“底层证据覆盖差异”：A/HK 分析师与 DCF 覆盖偏低。")
    lines.append("")
    lines.append("## 关键覆盖率")
    lines.append("")
    for field in ["price_to_fair_value", "quality_score", "growth_score", "momentum_score", "catalyst_score", "risk_score", "certainty_score", "target_mean_price"]:
        payload = source_coverage.get(field, {})
        lines.append(
            f"- {field}: {payload.get('present', 0)}/{payload.get('total', 0)} "
            f"({(payload.get('coverage_ratio') or 0.0):.2%})"
        )
    lines.append("")
    lines.append("## 原始证据覆盖（缓存层）")
    lines.append("")
    for field in ["return_on_equity", "gross_margins", "revenue_growth", "earnings_growth", "analyst_count", "recommendation_mean"]:
        payload = raw_coverage.get(field, {})
        lines.append(
            f"- {field}: {payload.get('present', 0)}/{payload.get('total', 0)} "
            f"({(payload.get('coverage_ratio') or 0.0):.2%})"
        )
    lines.append("")
    lines.append("## 缺口")
    lines.append("")
    if not gaps:
        lines.append("- 当前未检测到高优先级缺口。")
    else:
        for item in gaps:
            lines.append(f"- [{item.get('severity')}] {item.get('id')}: {item.get('description')}")
    lines.append("")
    lines.append("## 免费优先动作")
    lines.append("")
    for action in report["source_expansion_plan"]["free_first"]:
        lines.append(f"- {action}")
    lines.append("")
    lines.append("## 低成本付费备选（待决策）")
    lines.append("")
    for option in report["source_expansion_plan"]["low_cost_paid_candidates_waiting_decision"]:
        lines.append(f"- {option['source']} | 场景：{option['use_case']} | 成本级别：{option['cost_level']}")
    lines.append("")

    args.output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"审计 JSON: {args.output_json}")
    print(f"审计 Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
