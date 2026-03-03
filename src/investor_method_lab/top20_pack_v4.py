from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from investor_method_lab.scoring import FACTOR_KEYS, normalize_weights, parse_float, top_reasons
from investor_method_lab.top20_pack import GroupProfile

MARKET_KEYS = ("A", "HK", "US")
TIER_ORDER = ("core", "watch", "tactical")

DEFAULT_TIER_WEIGHTS = {
    "core": 1.0,
    "watch": 0.78,
    "tactical": 0.90,
    "rejected": 0.0,
}


def load_rulebook(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("rulebook payload must be object")
    if not isinstance(payload.get("groups"), list):
        raise ValueError("rulebook.groups must be array")
    return payload


def infer_market_from_ticker(ticker: str) -> str:
    value = str(ticker or "").strip().upper()
    if not value:
        return "US"
    if value.startswith(("SH.", "SZ.")) or value.endswith((".SS", ".SZ")):
        return "A"
    if value.startswith("HK.") or value.endswith(".HK"):
        return "HK"
    if value.startswith("US."):
        return "US"
    return "US"


def _percentile_rank(sorted_values: List[float], value: float) -> float:
    if not sorted_values:
        return 0.5
    left = bisect_left(sorted_values, value)
    right = bisect_right(sorted_values, value)
    rank = (left + right) / 2.0
    return rank / len(sorted_values)


def _raw_metrics(row: Dict[str, Any]) -> Dict[str, float]:
    price_to_fv = parse_float(row.get("price_to_fair_value"), 1.0)
    quality = parse_float(row.get("quality_score"), 50.0)
    growth = parse_float(row.get("growth_score"), 50.0)
    momentum = parse_float(row.get("momentum_score"), 50.0)
    catalyst = parse_float(row.get("catalyst_score"), 50.0)
    risk_score = parse_float(row.get("risk_score"), 50.0)
    risk_control = max(0.0, min(100.0, 100.0 - risk_score))
    certainty_raw = row.get("certainty_score")
    certainty = None
    if certainty_raw not in (None, ""):
        certainty = parse_float(certainty_raw, 0.0)
    return {
        "price_to_fair_value_raw": price_to_fv,
        "margin_of_safety_raw": 1.0 - price_to_fv,
        "quality_score_raw": quality,
        "growth_score_raw": growth,
        "momentum_score_raw": momentum,
        "catalyst_score_raw": catalyst,
        "risk_score_raw": risk_score,
        "risk_control_raw": risk_control,
        "certainty_score_raw": certainty,
    }


def prepare_rows_with_market_norm(opportunities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = [dict(row) for row in opportunities]
    markets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        market = infer_market_from_ticker(row.get("ticker", ""))
        row["market"] = row.get("market") or market
        metrics = _raw_metrics(row)
        row["_metrics_raw"] = metrics
        markets[market].append(row)

    metric_fields = [
        "margin_of_safety_raw",
        "quality_score_raw",
        "growth_score_raw",
        "momentum_score_raw",
        "catalyst_score_raw",
        "risk_control_raw",
    ]
    for market, market_rows in markets.items():
        sorted_map: Dict[str, List[float]] = {}
        for field in metric_fields:
            sorted_map[field] = sorted(float(r["_metrics_raw"][field]) for r in market_rows)
        for row in market_rows:
            raw = row["_metrics_raw"]
            row["market_norm_margin_of_safety"] = _percentile_rank(
                sorted_map["margin_of_safety_raw"], float(raw["margin_of_safety_raw"])
            )
            row["market_norm_quality"] = _percentile_rank(
                sorted_map["quality_score_raw"], float(raw["quality_score_raw"])
            )
            row["market_norm_growth"] = _percentile_rank(
                sorted_map["growth_score_raw"], float(raw["growth_score_raw"])
            )
            row["market_norm_momentum"] = _percentile_rank(
                sorted_map["momentum_score_raw"], float(raw["momentum_score_raw"])
            )
            row["market_norm_catalyst"] = _percentile_rank(
                sorted_map["catalyst_score_raw"], float(raw["catalyst_score_raw"])
            )
            row["market_norm_risk_control"] = _percentile_rank(
                sorted_map["risk_control_raw"], float(raw["risk_control_raw"])
            )
            row["market_norm_source_market"] = market

    return rows


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _op_compare(lhs: float, op: str, rhs: float) -> bool:
    if op == ">=":
        return lhs >= rhs
    if op == ">":
        return lhs > rhs
    if op == "<=":
        return lhs <= rhs
    if op == "<":
        return lhs < rhs
    if op == "==":
        return lhs == rhs
    raise ValueError(f"unsupported op: {op}")


def _is_near_miss(lhs: float, op: str, rhs: float, tolerance: float) -> bool:
    if tolerance <= 0:
        return False
    if op in (">=", ">"):
        return lhs >= rhs - tolerance
    if op in ("<=", "<"):
        return lhs <= rhs + tolerance
    return False


def _row_metric_value(row: Dict[str, Any], field: str) -> float | None:
    raw = row.get(field)
    if raw in (None, ""):
        return None
    return parse_float(raw, 0.0)


def _build_factor_contributions(row: Dict[str, Any], weights: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    factors = {
        "margin_of_safety": parse_float(row.get("market_norm_margin_of_safety"), 0.5),
        "quality": parse_float(row.get("market_norm_quality"), 0.5),
        "growth": parse_float(row.get("market_norm_growth"), 0.5),
        "momentum": parse_float(row.get("market_norm_momentum"), 0.5),
        "catalyst": parse_float(row.get("market_norm_catalyst"), 0.5),
        "risk_control": parse_float(row.get("market_norm_risk_control"), 0.5),
    }
    contributions: Dict[str, float] = {}
    score = 0.0
    for key in FACTOR_KEYS:
        contrib = factors[key] * weights.get(key, 0.0)
        contributions[key] = contrib
        score += contrib
    return score * 100.0, contributions


def _resolve_group_rule(group_id: str, market: str, rulebook: Dict[str, Any]) -> Dict[str, Any]:
    groups = rulebook.get("groups", [])
    group = next((item for item in groups if item.get("id") == group_id), None)
    if group is None:
        raise ValueError(f"group rule missing for {group_id}")
    default = group.get("default", {})
    override = (group.get("market_overrides") or {}).get(market, {})
    merged = dict(default)
    merged.update(override)
    merged["_name"] = group.get("name", group_id)
    merged["_core_hypothesis"] = group.get("core_hypothesis", "")
    merged["_risk_notes"] = group.get("risk_notes", [])
    merged["_false_negatives"] = group.get("common_false_negatives", [])
    merged["_tuning_suggestions"] = group.get("tuning_suggestions", [])
    return merged


def _evaluate_group_trace(
    row: Dict[str, Any],
    profile: GroupProfile,
    rulebook: Dict[str, Any],
) -> Dict[str, Any]:
    market = str(row.get("market") or infer_market_from_ticker(row.get("ticker", "")))
    weights = normalize_weights(profile.weights)
    base_score, contributions = _build_factor_contributions(row, weights)

    rule = _resolve_group_rule(profile.id, market, rulebook)
    defaults = rulebook.get("defaults", {})
    hard_rules = list(rule.get("hard_rules") or [])
    soft_rules = list(rule.get("soft_rules") or [])
    tiering = dict(defaults.get("tiering") or {})
    tiering.update(rule.get("tiering") or {})

    hard_fail_reasons: List[str] = []
    hard_pass_rules: List[str] = []
    near_miss = False
    default_tolerance = parse_float(defaults.get("near_miss_tolerance"), 0.05)

    for item in hard_rules:
        field = str(item.get("field") or "").strip()
        if not field:
            continue
        op = str(item.get("op") or ">=").strip()
        rhs = parse_float(item.get("value"), 0.0)
        lhs = _row_metric_value(row, field)
        if lhs is None and field in row.get("_metrics_raw", {}):
            lhs = row["_metrics_raw"][field]
        if lhs is None:
            lhs = 0.0
        label = str(item.get("label") or f"{field}{op}{rhs}")
        tolerance = parse_float(item.get("near_miss_tolerance"), default_tolerance)
        if _op_compare(float(lhs), op, rhs):
            hard_pass_rules.append(label)
        else:
            hard_fail_reasons.append(label)
            if _is_near_miss(float(lhs), op, rhs, tolerance):
                near_miss = True

    hard_pass = len(hard_fail_reasons) == 0
    penalty_multiplier = 1.0
    soft_penalties: List[Dict[str, Any]] = []
    for item in soft_rules:
        field = str(item.get("field") or "").strip()
        if not field:
            continue
        op = str(item.get("op") or "<").strip()
        rhs = parse_float(item.get("value"), 0.0)
        lhs = _row_metric_value(row, field)
        if lhs is None and field in row.get("_metrics_raw", {}):
            lhs = row["_metrics_raw"][field]
        if lhs is None:
            lhs = 0.0
        multiplier = parse_float(item.get("multiplier"), 1.0)
        label = str(item.get("label") or f"{field}{op}{rhs}")
        triggered = _op_compare(float(lhs), op, rhs)
        soft_penalties.append(
            {
                "rule": label,
                "field": field,
                "op": op,
                "threshold": rhs,
                "value": float(lhs),
                "multiplier": multiplier,
                "triggered": triggered,
            }
        )
        if triggered:
            penalty_multiplier *= multiplier

    core_min = parse_float(tiering.get("core_min_score"), 70.0)
    tactical_min = parse_float(tiering.get("tactical_min_score"), 55.0)
    watch_multiplier = parse_float(tiering.get("watch_multiplier"), 0.80)

    if hard_pass:
        adjusted_score = base_score * penalty_multiplier
        if adjusted_score >= core_min:
            tier = "core"
            tier_reason = "通过硬筛且分数达到核心阈值"
        elif adjusted_score >= tactical_min:
            tier = "tactical"
            tier_reason = "通过硬筛但分数位于战术区间"
        else:
            tier = "tactical"
            tier_reason = "通过硬筛但分数偏低，归入战术观察"
    else:
        if near_miss:
            tier = "watch"
            adjusted_score = base_score * watch_multiplier
            tier_reason = "未通过硬筛，但接近阈值（near-miss）"
        else:
            tier = "rejected"
            adjusted_score = 0.0
            tier_reason = "未通过硬筛，且不在near-miss范围"

    tier_weights = dict(DEFAULT_TIER_WEIGHTS)
    tier_weights.update(rulebook.get("tier_weights") or {})
    weighted_contribution = adjusted_score * profile.group_weight * parse_float(tier_weights.get(tier), 0.0)

    reason = " | ".join(top_reasons(contributions, top_n=2))
    metrics_raw = row.get("_metrics_raw", {})
    metrics_snapshot = {
        "market": market,
        "price_to_fair_value_raw": parse_float(metrics_raw.get("price_to_fair_value_raw"), 1.0),
        "margin_of_safety_raw": parse_float(metrics_raw.get("margin_of_safety_raw"), 0.0),
        "quality_score_raw": parse_float(metrics_raw.get("quality_score_raw"), 0.0),
        "growth_score_raw": parse_float(metrics_raw.get("growth_score_raw"), 0.0),
        "momentum_score_raw": parse_float(metrics_raw.get("momentum_score_raw"), 0.0),
        "catalyst_score_raw": parse_float(metrics_raw.get("catalyst_score_raw"), 0.0),
        "risk_control_raw": parse_float(metrics_raw.get("risk_control_raw"), 0.0),
        "certainty_score_raw": metrics_raw.get("certainty_score_raw"),
        "market_norm_margin_of_safety": parse_float(row.get("market_norm_margin_of_safety"), 0.5),
        "market_norm_quality": parse_float(row.get("market_norm_quality"), 0.5),
        "market_norm_growth": parse_float(row.get("market_norm_growth"), 0.5),
        "market_norm_momentum": parse_float(row.get("market_norm_momentum"), 0.5),
        "market_norm_catalyst": parse_float(row.get("market_norm_catalyst"), 0.5),
        "market_norm_risk_control": parse_float(row.get("market_norm_risk_control"), 0.5),
    }

    return {
        "group_id": profile.id,
        "group_name": profile.name,
        "group_weight": round(profile.group_weight, 6),
        "hard_pass": hard_pass,
        "hard_pass_rules": hard_pass_rules,
        "hard_fail_reasons": hard_fail_reasons,
        "near_miss": near_miss,
        "soft_penalties": soft_penalties,
        "penalty_multiplier": round(penalty_multiplier, 6),
        "base_score": round(base_score, 4),
        "adjusted_score": round(adjusted_score, 4),
        "tier": tier,
        "tier_reason": tier_reason,
        "weighted_contribution": round(weighted_contribution, 4),
        "factor_contributions": {
            key: round(contributions.get(key, 0.0) * 100.0, 4) for key in FACTOR_KEYS
        },
        "reason": reason,
        "metrics_snapshot": metrics_snapshot,
        "rulebook_notes": {
            "core_hypothesis": rule.get("_core_hypothesis", ""),
            "risk_notes": rule.get("_risk_notes", []),
            "false_negatives": rule.get("_false_negatives", []),
            "tuning_suggestions": rule.get("_tuning_suggestions", []),
        },
    }


def _best_trace(traces: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    candidates = [item for item in traces if item.get("tier") != "rejected"]
    if not candidates:
        return None
    return max(candidates, key=lambda item: parse_float(item.get("weighted_contribution"), 0.0))


def _group_stats_from_traces(
    profiles: List[GroupProfile], trace_by_ticker: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    for profile in profiles:
        row = {"core": 0, "watch": 0, "tactical": 0, "rejected": 0}
        for traces in trace_by_ticker.values():
            trace = next((item for item in traces if item.get("group_id") == profile.id), None)
            if trace is None:
                continue
            tier = str(trace.get("tier") or "rejected")
            if tier not in row:
                tier = "rejected"
            row[tier] += 1
        stats[profile.id] = row
    return stats


def _pick_top_rows(rows: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda item: parse_float(item.get("composite_score"), 0.0), reverse=True)
    return sorted_rows[:top_n]


def _pick_diversified(rows: List[Dict[str, Any]], top_n: int, max_per_sector: int) -> List[Dict[str, Any]]:
    if max_per_sector <= 0:
        raise ValueError("max_per_sector must be >=1")
    selected: List[Dict[str, Any]] = []
    selected_tickers: set[str] = set()
    sector_count: Dict[str, int] = {}
    for row in sorted(rows, key=lambda item: parse_float(item.get("composite_score"), 0.0), reverse=True):
        sector = str(row.get("sector") or "Unknown")
        if sector_count.get(sector, 0) >= max_per_sector:
            continue
        selected.append(row)
        selected_tickers.add(str(row.get("ticker") or ""))
        sector_count[sector] = sector_count.get(sector, 0) + 1
        if len(selected) >= top_n:
            return selected
    for row in sorted(rows, key=lambda item: parse_float(item.get("composite_score"), 0.0), reverse=True):
        ticker = str(row.get("ticker") or "")
        if ticker in selected_tickers:
            continue
        selected.append(row)
        if len(selected) >= top_n:
            break
    return selected


def build_v4_analysis(
    opportunities: Iterable[Dict[str, Any]],
    profiles: List[GroupProfile],
    rulebook: Dict[str, Any],
    *,
    top_n: int = 10,
    max_per_sector: int = 2,
    per_group_top_n: int = 5,
    per_tier_top_n: int = 10,
) -> Dict[str, Any]:
    rows = prepare_rows_with_market_norm(opportunities)
    trace_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    composite_rows: List[Dict[str, Any]] = []
    group_rows_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    tiered_rows: List[Dict[str, Any]] = []

    for row in rows:
        ticker = str(row.get("ticker") or "")
        traces: List[Dict[str, Any]] = []
        composite_score = 0.0
        for profile in profiles:
            trace = _evaluate_group_trace(row, profile, rulebook)
            traces.append(trace)
            if trace.get("tier") != "rejected":
                composite_score += parse_float(trace.get("weighted_contribution"), 0.0)

                group_row = dict(row)
                group_row["group_id"] = profile.id
                group_row["group_name"] = profile.name
                group_row["group_score"] = round(parse_float(trace.get("adjusted_score"), 0.0), 2)
                group_row["base_score"] = round(parse_float(trace.get("base_score"), 0.0), 2)
                group_row["penalty_multiplier"] = round(parse_float(trace.get("penalty_multiplier"), 1.0), 4)
                group_row["tier"] = trace.get("tier", "")
                group_row["hard_pass"] = bool(trace.get("hard_pass"))
                group_row["hard_fail_reasons"] = "；".join(trace.get("hard_fail_reasons", []))
                group_row["soft_penalties"] = "；".join(
                    item.get("rule", "")
                    for item in trace.get("soft_penalties", [])
                    if item.get("triggered")
                )
                group_row["reason"] = trace.get("reason", "")
                group_row["margin_of_safety"] = round(
                    parse_float(row.get("_metrics_raw", {}).get("margin_of_safety_raw"), 0.0) * 100.0,
                    1,
                )
                group_row["risk_control"] = round(
                    parse_float(row.get("_metrics_raw", {}).get("risk_control_raw"), 0.0),
                    1,
                )
                group_row["trace_id"] = f"{ticker}:{profile.id}:{trace.get('tier', 'rejected')}"
                group_rows_map[profile.id].append(group_row)

        trace_by_ticker[ticker] = traces
        best_trace = _best_trace(traces)
        if best_trace is None:
            continue

        pass_count = sum(1 for item in traces if item.get("hard_pass") is True)
        fail_count = len(traces) - pass_count
        composite_row = dict(row)
        composite_row["composite_score"] = round(composite_score, 2)
        composite_row["best_group"] = str(best_trace.get("group_name") or "")
        composite_row["best_reason"] = str(best_trace.get("reason") or "")
        composite_row["margin_of_safety"] = round(
            parse_float(row.get("_metrics_raw", {}).get("margin_of_safety_raw"), 0.0) * 100.0, 1
        )
        composite_row["risk_control"] = round(
            parse_float(row.get("_metrics_raw", {}).get("risk_control_raw"), 0.0), 1
        )
        composite_row["explain_best_group_id"] = str(best_trace.get("group_id") or "")
        composite_row["explain_best_group_weighted_contribution"] = round(
            parse_float(best_trace.get("weighted_contribution"), 0.0), 4
        )
        composite_row["explain_passed_group_count"] = pass_count
        composite_row["explain_failed_group_count"] = fail_count
        composite_row["explain_market"] = str(row.get("market") or "")
        composite_row["explain_group_trace_json"] = _safe_json(traces)
        composite_rows.append(composite_row)

    group_top_rows: List[Tuple[GroupProfile, List[Dict[str, Any]]]] = []
    for profile in profiles:
        group_rows = sorted(
            group_rows_map.get(profile.id, []),
            key=lambda item: parse_float(item.get("group_score"), 0.0),
            reverse=True,
        )
        group_top_rows.append((profile, group_rows[:per_group_top_n]))
        by_tier: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in group_rows:
            by_tier[str(row.get("tier") or "rejected")].append(row)
        for tier in TIER_ORDER:
            tier_rows = by_tier.get(tier, [])
            for idx, row in enumerate(tier_rows[:per_tier_top_n], start=1):
                item = dict(row)
                item["group_rank"] = idx
                tiered_rows.append(item)

    top_rows = _pick_top_rows(composite_rows, top_n=top_n)
    diversified_rows = _pick_diversified(composite_rows, top_n=top_n, max_per_sector=max_per_sector)
    group_stats = _group_stats_from_traces(profiles, trace_by_ticker)

    decision_trace_rows: List[Dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "")
        decision_trace_rows.append(
            {
                "ticker": ticker,
                "name": row.get("name", ""),
                "sector": row.get("sector", ""),
                "market": row.get("market", ""),
                "composite_score": next(
                    (
                        parse_float(item.get("composite_score"), 0.0)
                        for item in composite_rows
                        if item.get("ticker") == ticker
                    ),
                    0.0,
                ),
                "metrics_raw": row.get("_metrics_raw", {}),
                "metrics_market_norm": {
                    "margin_of_safety": row.get("market_norm_margin_of_safety"),
                    "quality": row.get("market_norm_quality"),
                    "growth": row.get("market_norm_growth"),
                    "momentum": row.get("market_norm_momentum"),
                    "catalyst": row.get("market_norm_catalyst"),
                    "risk_control": row.get("market_norm_risk_control"),
                },
                "groups": trace_by_ticker.get(ticker, []),
            }
        )

    return {
        "top_rows": top_rows,
        "group_top_rows": group_top_rows,
        "diversified_rows": diversified_rows,
        "tiered_group_rows": tiered_rows,
        "trace_by_ticker": trace_by_ticker,
        "decision_trace_rows": decision_trace_rows,
        "group_stats": group_stats,
    }


def render_methodology_playbook_v4(
    *,
    as_of_date: str,
    profiles: List[GroupProfile],
    rulebook: Dict[str, Any],
    group_stats: Dict[str, Dict[str, int]],
) -> str:
    group_map = {item.get("id"): item for item in rulebook.get("groups", [])}
    lines: List[str] = []
    lines.append("# 方法论筛选引擎 V4 Playbook")
    lines.append("")
    lines.append(f"更新时间：{as_of_date}")
    lines.append(f"生成时间(UTC)：{datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## 全局设置")
    lines.append("")
    lines.append(f"- 版本：{rulebook.get('version', 'v4')}")
    lines.append(f"- 目标函数：{rulebook.get('goal', '平衡覆盖与质量')}")
    lines.append(f"- 层级权重：{json.dumps(rulebook.get('tier_weights', DEFAULT_TIER_WEIGHTS), ensure_ascii=False)}")
    lines.append("")

    for profile in profiles:
        cfg = group_map.get(profile.id) or {}
        lines.append(f"## {profile.name}（{profile.id}）")
        lines.append("")
        lines.append(f"- 核心假设：{cfg.get('core_hypothesis', '-')} ")
        lines.append(f"- 适用市场：{', '.join(cfg.get('suitable_markets', MARKET_KEYS))}")
        stats = group_stats.get(profile.id, {})
        lines.append(
            "- 当前覆盖："
            f"core={stats.get('core', 0)}，watch={stats.get('watch', 0)}，"
            f"tactical={stats.get('tactical', 0)}，rejected={stats.get('rejected', 0)}"
        )
        lines.append("")

        default = cfg.get("default", {})
        lines.append("### 默认规则")
        lines.append("")
        lines.append("- 硬筛：")
        for item in default.get("hard_rules", []):
            lines.append(f"  - {item.get('label', '-')}")
        lines.append("- 软惩罚：")
        for item in default.get("soft_rules", []):
            lines.append(f"  - {item.get('label', '-')}, x{item.get('multiplier', 1.0)}")
        lines.append("")

        overrides = cfg.get("market_overrides", {})
        for market in MARKET_KEYS:
            ov = overrides.get(market)
            if not ov:
                continue
            lines.append(f"### {market} 市场覆盖")
            lines.append("")
            lines.append("- 硬筛覆盖：")
            for item in ov.get("hard_rules", []):
                lines.append(f"  - {item.get('label', '-')}")
            lines.append("- 软惩罚覆盖：")
            for item in ov.get("soft_rules", []):
                lines.append(f"  - {item.get('label', '-')}, x{item.get('multiplier', 1.0)}")
            lines.append("")

        false_neg = cfg.get("common_false_negatives", [])
        risk_notes = cfg.get("risk_notes", [])
        tuning = cfg.get("tuning_suggestions", [])
        if false_neg:
            lines.append("### 典型误杀")
            for item in false_neg:
                lines.append(f"- {item}")
            lines.append("")
        if risk_notes:
            lines.append("### 风险提示")
            for item in risk_notes:
                lines.append(f"- {item}")
            lines.append("")
        if tuning:
            lines.append("### 调参建议")
            for item in tuning:
                lines.append(f"- {item}")
            lines.append("")

        change_log = cfg.get("change_log", [])
        if change_log:
            lines.append("### 最近变更")
            for item in change_log[:5]:
                if isinstance(item, dict):
                    date = item.get("date", "-")
                    summary = item.get("summary", "-")
                    lines.append(f"- {date}：{summary}")
                else:
                    lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"
