from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from investor_method_lab.scoring import (
    normalize_weights,
    parse_float,
    score_opportunity,
    top_reasons,
)


@dataclass
class GroupProfile:
    id: str
    name: str
    core_question: str
    weights: Dict[str, float]
    members: List[Dict[str, Any]]
    group_weight: float
    bucket_matches: List[str]


VALUE_QUALITY_COMPOUND_RULES = {
    "min_margin_of_safety": 0.15,
    "preferred_margin_of_safety": 0.30,
    "min_certainty_score": 65.0,
    "soft_certainty_score": 75.0,
    "margin_soft_penalty": 0.88,
    "certainty_soft_penalty": 0.92,
}

GROUP_RULE_TEXTS: Dict[str, Dict[str, str]] = {
    "value_quality_compound": {
        "hard": "MOS>=15%，质量>=65；若有确定性分则>=65。",
        "soft": "MOS<30% 折扣0.88；确定性<75 折扣0.92。",
    },
    "industry_compounder": {
        "hard": "MOS>=5%，质量>=70，风控>=45%。",
        "soft": "成长<55 折扣0.93；催化<50 折扣0.95。",
    },
    "garp_growth": {
        "hard": "成长>=55，质量>=60，P/FV<=1.25，风控>=35%。",
        "soft": "P/FV>1.05 折扣0.90；趋势<55 折扣0.93。",
    },
    "deep_value_recovery": {
        "hard": "MOS>=20%，催化>=50，风控>=30%。",
        "soft": "质量<45 折扣0.90；趋势<40 折扣0.92。",
    },
    "macro_regime": {
        "hard": "趋势>=55，催化>=55，风控>=30%。",
        "soft": "成长<45 折扣0.95；MOS<0 折扣0.95。",
    },
    "trend_following": {
        "hard": "趋势>=70，催化>=60，风控>=30%。",
        "soft": "P/FV>1.20 折扣0.90；质量<45 折扣0.93。",
    },
    "systematic_quant": {
        "hard": "质量/成长/趋势/催化均>=45，风控>=35%。",
        "soft": "MOS<0 折扣0.93。",
    },
    "event_driven_activist": {
        "hard": "催化>=55，趋势>=40，风控>=30%，且P/FV<=1.80。",
        "soft": "MOS<5% 折扣0.95；质量<50 折扣0.95。",
    },
    "credit_cycle": {
        "hard": "MOS>=5%，催化>=50，风控>=45%。",
        "soft": "趋势<50 折扣0.95；质量<45 折扣0.95。",
    },
}


def _get_weights(
    spec: Dict[str, Any], strategy_by_id: Dict[str, Dict[str, Any]]
) -> Dict[str, float]:
    if "custom_weights" in spec:
        return normalize_weights(spec["custom_weights"])

    strategy_id = spec.get("base_strategy_id")
    if not strategy_id or strategy_id not in strategy_by_id:
        raise ValueError(f"Unknown base strategy: {strategy_id}")
    return normalize_weights(strategy_by_id[strategy_id].get("weights", {}))


def build_group_profiles(
    investors: Iterable[Dict[str, Any]],
    framework: Dict[str, Any],
    strategies: Iterable[Dict[str, Any]],
) -> List[GroupProfile]:
    investor_list = list(investors)
    strategy_by_id = {item.get("id"): item for item in strategies}

    profiles: List[GroupProfile] = []
    total_members = 0

    for spec in framework.get("groups", []):
        buckets = set(spec.get("bucket_matches", []))
        members = [
            investor
            for investor in investor_list
            if investor.get("methodology_bucket") in buckets
        ]
        if not members:
            continue

        weights = _get_weights(spec, strategy_by_id)
        total_members += len(members)
        profiles.append(
            GroupProfile(
                id=spec.get("id", ""),
                name=spec.get("name", ""),
                core_question=spec.get("core_question", ""),
                weights=weights,
                members=members,
                group_weight=0.0,
                bucket_matches=sorted(buckets),
            )
        )

    if total_members == 0:
        return profiles

    for profile in profiles:
        profile.group_weight = len(profile.members) / total_members

    return profiles


def _format_member_names(members: List[Dict[str, Any]]) -> str:
    return "、".join(item.get("name_cn", item.get("name_en", "")) for item in members)


def _optional_score(row: Dict[str, Any], key: str) -> float | None:
    raw = row.get(key)
    if raw in (None, ""):
        return None
    return parse_float(raw, 0.0)


def _row_metrics(row: Dict[str, Any]) -> Dict[str, float | None]:
    price_to_fair_value = parse_float(row.get("price_to_fair_value"), 1.0)
    quality = parse_float(row.get("quality_score"), 50.0)
    growth = parse_float(row.get("growth_score"), 50.0)
    momentum = parse_float(row.get("momentum_score"), 50.0)
    catalyst = parse_float(row.get("catalyst_score"), 50.0)
    risk_score = parse_float(row.get("risk_score"), 50.0)
    risk_control = max(0.0, min(100.0, 100.0 - risk_score))
    return {
        "price_to_fair_value": price_to_fair_value,
        "margin_of_safety": 1.0 - price_to_fair_value,
        "quality_score": quality,
        "growth_score": growth,
        "momentum_score": momentum,
        "catalyst_score": catalyst,
        "risk_score": risk_score,
        "risk_control_pct": risk_control,
        "certainty_score": _optional_score(row, "certainty_score"),
    }


def _apply_group_rules(
    profile: GroupProfile,
    row: Dict[str, Any],
    score: float,
) -> Tuple[bool, float]:
    metrics = _row_metrics(row)
    margin_of_safety = float(metrics["margin_of_safety"] or 0.0)
    quality_score = float(metrics["quality_score"] or 0.0)
    growth_score = float(metrics["growth_score"] or 0.0)
    momentum_score = float(metrics["momentum_score"] or 0.0)
    catalyst_score = float(metrics["catalyst_score"] or 0.0)
    risk_control_pct = float(metrics["risk_control_pct"] or 0.0)
    certainty_score = metrics["certainty_score"]
    adjusted = score

    if profile.id == "value_quality_compound":
        if margin_of_safety < VALUE_QUALITY_COMPOUND_RULES["min_margin_of_safety"]:
            return False, 0.0
        if quality_score < 65.0:
            return False, 0.0
        if (
            certainty_score is not None
            and certainty_score < VALUE_QUALITY_COMPOUND_RULES["min_certainty_score"]
        ):
            return False, 0.0

        if margin_of_safety < VALUE_QUALITY_COMPOUND_RULES["preferred_margin_of_safety"]:
            adjusted *= VALUE_QUALITY_COMPOUND_RULES["margin_soft_penalty"]
        if (
            certainty_score is not None
            and certainty_score < VALUE_QUALITY_COMPOUND_RULES["soft_certainty_score"]
        ):
            adjusted *= VALUE_QUALITY_COMPOUND_RULES["certainty_soft_penalty"]

        return True, adjusted

    if profile.id == "industry_compounder":
        if margin_of_safety < 0.05 or quality_score < 70.0 or risk_control_pct < 45.0:
            return False, 0.0
        if growth_score < 55.0:
            adjusted *= 0.93
        if catalyst_score < 50.0:
            adjusted *= 0.95
        return True, adjusted

    if profile.id == "garp_growth":
        if (
            growth_score < 55.0
            or quality_score < 60.0
            or float(metrics["price_to_fair_value"] or 1.0) > 1.25
            or risk_control_pct < 35.0
        ):
            return False, 0.0
        if float(metrics["price_to_fair_value"] or 1.0) > 1.05:
            adjusted *= 0.90
        if momentum_score < 55.0:
            adjusted *= 0.93
        return True, adjusted

    if profile.id == "deep_value_recovery":
        if margin_of_safety < 0.20 or catalyst_score < 50.0 or risk_control_pct < 30.0:
            return False, 0.0
        if quality_score < 45.0:
            adjusted *= 0.90
        if momentum_score < 40.0:
            adjusted *= 0.92
        return True, adjusted

    if profile.id == "macro_regime":
        if momentum_score < 55.0 or catalyst_score < 55.0 or risk_control_pct < 30.0:
            return False, 0.0
        if growth_score < 45.0:
            adjusted *= 0.95
        if margin_of_safety < 0.0:
            adjusted *= 0.95
        return True, adjusted

    if profile.id == "trend_following":
        if momentum_score < 70.0 or catalyst_score < 60.0 or risk_control_pct < 30.0:
            return False, 0.0
        if float(metrics["price_to_fair_value"] or 1.0) > 1.20:
            adjusted *= 0.90
        if quality_score < 45.0:
            adjusted *= 0.93
        return True, adjusted

    if profile.id == "systematic_quant":
        if (
            quality_score < 45.0
            or growth_score < 45.0
            or momentum_score < 45.0
            or catalyst_score < 45.0
            or risk_control_pct < 35.0
        ):
            return False, 0.0
        if margin_of_safety < 0.0:
            adjusted *= 0.93
        return True, adjusted

    if profile.id == "event_driven_activist":
        if (
            catalyst_score < 55.0
            or momentum_score < 40.0
            or risk_control_pct < 30.0
            or float(metrics["price_to_fair_value"] or 1.0) > 1.80
        ):
            return False, 0.0
        if margin_of_safety < 0.05:
            adjusted *= 0.95
        if quality_score < 50.0:
            adjusted *= 0.95
        return True, adjusted

    if profile.id == "credit_cycle":
        if margin_of_safety < 0.05 or catalyst_score < 50.0 or risk_control_pct < 45.0:
            return False, 0.0
        if momentum_score < 50.0:
            adjusted *= 0.95
        if quality_score < 45.0:
            adjusted *= 0.95
        return True, adjusted

    return True, adjusted


def _score_row_for_weights(
    row: Dict[str, Any],
    profile: GroupProfile,
    weights: Dict[str, float],
    score_key: str = "score",
) -> Dict[str, Any] | None:
    score, factors, contributions = score_opportunity(row, weights)
    eligible, adjusted_score = _apply_group_rules(profile, row, score)
    if not eligible:
        return None

    item = dict(row)
    item[score_key] = round(adjusted_score, 2)
    item["reason"] = " | ".join(top_reasons(contributions, top_n=2))
    item["margin_of_safety"] = round(factors.get("margin_of_safety", 0.0) * 100, 1)
    item["risk_control"] = round(factors.get("risk_control", 0.0) * 100, 1)
    return item


def rank_opportunities_for_each_group(
    opportunities: Iterable[Dict[str, Any]],
    profiles: List[GroupProfile],
    top_n_per_group: int = 5,
) -> List[Tuple[GroupProfile, List[Dict[str, Any]]]]:
    opportunity_list = [dict(row) for row in opportunities]
    ranked_by_group: List[Tuple[GroupProfile, List[Dict[str, Any]]]] = []

    for profile in profiles:
        rows = []
        for row in opportunity_list:
            scored = _score_row_for_weights(
                row,
                profile=profile,
                weights=profile.weights,
                score_key="group_score",
            )
            if scored is not None:
                rows.append(scored)
        rows.sort(key=lambda x: x["group_score"], reverse=True)
        ranked_by_group.append((profile, rows[:top_n_per_group]))

    return ranked_by_group


def _rank_composite_opportunities(
    opportunities: Iterable[Dict[str, Any]],
    profiles: List[GroupProfile],
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []

    for row in opportunities:
        row_dict = dict(row)

        total_score = 0.0
        best_group_name = ""
        best_group_weighted = -1.0
        best_group_reasons: List[str] = []
        best_group_factors: Dict[str, float] = {}

        for profile in profiles:
            score, factors, contributions = score_opportunity(row_dict, profile.weights)
            eligible, adjusted_score = _apply_group_rules(profile, row_dict, score)
            if not eligible:
                continue

            weighted = adjusted_score * profile.group_weight
            total_score += weighted

            if weighted > best_group_weighted:
                best_group_weighted = weighted
                best_group_name = profile.name
                best_group_reasons = top_reasons(contributions, top_n=2)
                best_group_factors = factors

        if best_group_weighted < 0:
            continue

        row_dict["composite_score"] = round(total_score, 2)
        row_dict["best_group"] = best_group_name
        row_dict["best_reason"] = " | ".join(best_group_reasons)
        row_dict["margin_of_safety"] = round(best_group_factors.get("margin_of_safety", 0.0) * 100, 1)
        row_dict["risk_control"] = round(best_group_factors.get("risk_control", 0.0) * 100, 1)
        ranked.append(row_dict)

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    return ranked


def rank_first_batch_opportunities(
    opportunities: Iterable[Dict[str, Any]],
    profiles: List[GroupProfile],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    return _rank_composite_opportunities(opportunities, profiles)[:top_n]


def rank_diversified_opportunities(
    opportunities: Iterable[Dict[str, Any]],
    profiles: List[GroupProfile],
    top_n: int = 10,
    max_per_sector: int = 2,
) -> List[Dict[str, Any]]:
    if max_per_sector <= 0:
        raise ValueError("max_per_sector must be >= 1")

    ranked_all = _rank_composite_opportunities(opportunities, profiles)
    selected: List[Dict[str, Any]] = []
    selected_tickers = set()
    sector_count: Dict[str, int] = {}

    for row in ranked_all:
        sector = str(row.get("sector", "") or "Unknown")
        if sector_count.get(sector, 0) >= max_per_sector:
            continue
        selected.append(row)
        selected_tickers.add(row.get("ticker", ""))
        sector_count[sector] = sector_count.get(sector, 0) + 1
        if len(selected) >= top_n:
            return selected

    for row in ranked_all:
        ticker = row.get("ticker", "")
        if ticker in selected_tickers:
            continue
        selected.append(row)
        if len(selected) >= top_n:
            break

    return selected


def _weight_to_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _escape_md_cell(value: Any) -> str:
    text = str(value)
    text = text.replace("|", "\\|")
    return text.replace("\n", "<br>")


def _group_rule_text(profile_id: str) -> Tuple[str, str]:
    rule = GROUP_RULE_TEXTS.get(profile_id, {})
    return rule.get("hard", "默认硬筛：无"), rule.get("soft", "默认软惩罚：无")


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: Any, digits: int = 2) -> str:
    number = _optional_float(value)
    if number is None:
        return "-"
    return f"{number:.{digits}f}"


def _format_pct(value: Any, digits: int = 1, *, signed: bool = False) -> str:
    number = _optional_float(value)
    if number is None:
        return "-"
    if signed:
        return f"{number * 100:+.{digits}f}%"
    return f"{number * 100:.{digits}f}%"


def build_validation_summary(row: Dict[str, Any]) -> str:
    status = str(row.get("validation_status") or "").strip()
    if not status:
        return "-"
    parts = [status]
    hit = row.get("validation_hit")
    if hit is True:
        parts.append("命中")
    elif hit is False:
        parts.append("未命中")
    excess = _optional_float(row.get("validation_primary_excess_return"))
    if excess is not None:
        parts.append(f"超额{excess * 100:+.1f}%")
    days_held = _optional_float(row.get("validation_days_held"))
    if days_held is not None and days_held > 0:
        parts.append(f"{int(days_held)}d")
    return " | ".join(parts)


def build_valuation_summary(row: Dict[str, Any]) -> str:
    valuation_source = str(row.get("valuation_source") or row.get("valuation_source_at_signal") or "").strip()
    fair_value = _optional_float(row.get("fair_value") or row.get("fair_value_at_signal"))
    dcf_value = _optional_float(row.get("dcf_iv_base"))
    target_mean = _optional_float(row.get("target_mean_price"))

    parts: List[str] = []
    if valuation_source:
        parts.append(valuation_source)
    if valuation_source == "dcf_iv_base" and dcf_value is not None:
        parts.append(f"DCF {_format_number(dcf_value)}")
    elif fair_value is not None:
        parts.append(f"FV {_format_number(fair_value)}")
    if target_mean is not None and (dcf_value is not None or valuation_source != "target_mean_price"):
        parts.append(f"外部 {_format_number(target_mean)}")
    elif target_mean is not None and fair_value is None:
        parts.append(f"外部 {_format_number(target_mean)}")
    return " | ".join(parts) if parts else "-"


def build_risk_summary(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    valuation_source = str(row.get("valuation_source") or "").strip()
    if valuation_source == "close_fallback":
        parts.append("仅现价回退")

    dcf_quality = str(row.get("dcf_quality_gate_status") or "").strip()
    if dcf_quality in {"review", "caution", "warn", "fail"}:
        parts.append(f"DCF质量:{dcf_quality}")

    dcf_crosscheck = str(row.get("dcf_comps_crosscheck_status") or "").strip()
    if dcf_crosscheck in {"review", "warn", "unavailable", "fail"}:
        parts.append(f"交叉验证:{dcf_crosscheck}")

    review_state = str(row.get("review_state") or "").strip()
    if review_state and review_state != "auto":
        parts.append(f"复核:{review_state}")

    validation_status = str(row.get("validation_status") or "").strip()
    validation_hit = row.get("validation_hit")
    if validation_status == "expired":
        parts.append("历史信号已过期")
    elif validation_status == "closed" and validation_hit is False:
        parts.append("历史信号未命中")

    return " | ".join(parts) if parts else "-"


def render_opportunity_pack_markdown(
    as_of_date: str,
    profiles: List[GroupProfile],
    top_rows: List[Dict[str, Any]],
    group_top_rows: List[Tuple[GroupProfile, List[Dict[str, Any]]]] | None = None,
    diversified_rows: List[Dict[str, Any]] | None = None,
    per_group_top_n: int = 5,
    max_per_sector: int = 2,
) -> str:
    lines: List[str] = []
    lines.append("# Top20 方法论机会包")
    lines.append("")
    lines.append(f"更新时间：{as_of_date}")
    lines.append("")

    lines.append("## 1) 方法论分组")
    lines.append("")
    lines.append("| 分组 | 核心问题 | 代表投资人 | 人数 | 组合权重 |")
    lines.append("|---|---|---|---:|---:|")
    for profile in profiles:
        lines.append(
            f"| {_escape_md_cell(profile.name)} | {_escape_md_cell(profile.core_question)} | "
            f"{_escape_md_cell(_format_member_names(profile.members))} | "
            f"{len(profile.members)} | {_weight_to_pct(profile.group_weight)} |"
        )

    lines.append("")
    lines.append("## 2) 因子权重")
    lines.append("")
    lines.append("| 分组 | 安全边际 | 质量 | 成长 | 趋势 | 催化 | 风控 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for profile in profiles:
        w = profile.weights
        lines.append(
            f"| {_escape_md_cell(profile.name)} | {_weight_to_pct(w.get('margin_of_safety', 0.0))} | "
            f"{_weight_to_pct(w.get('quality', 0.0))} | {_weight_to_pct(w.get('growth', 0.0))} | "
            f"{_weight_to_pct(w.get('momentum', 0.0))} | {_weight_to_pct(w.get('catalyst', 0.0))} | "
            f"{_weight_to_pct(w.get('risk_control', 0.0))} |"
        )

    lines.append("")
    lines.append("### 执行规则（统一口径）")
    lines.append("")
    lines.append("| 分组 | 硬筛条件 | 软惩罚 |")
    lines.append("|---|---|---|")
    for profile in profiles:
        hard_text, soft_text = _group_rule_text(profile.id)
        lines.append(
            f"| {_escape_md_cell(profile.name)} | {_escape_md_cell(hard_text)} | {_escape_md_cell(soft_text)} |"
        )

    lines.append("")
    lines.append("## 3) 首批机会池 TOP10（组合评分）")
    lines.append("")
    lines.append("| 排名 | 代码 | 公司 | 行业 | 组合分 | 最匹配方法论 | 机会验真 | 估值联动 | 风险提示 | 可信度 | 来源摘要 | 原始理由 | 原始备注 |")
    lines.append("|---|---|---|---|---:|---|---|---|---|---|---|---|---|")
    for idx, row in enumerate(top_rows, start=1):
        lines.append(
            f"| {idx} | {_escape_md_cell(row.get('ticker', ''))} | {_escape_md_cell(row.get('name', ''))} | "
            f"{_escape_md_cell(row.get('sector', ''))} | {row.get('composite_score', 0.0):.2f} | "
            f"{_escape_md_cell(row.get('best_group', ''))} | {_escape_md_cell(build_validation_summary(row))} | "
            f"{_escape_md_cell(build_valuation_summary(row))} | {_escape_md_cell(build_risk_summary(row))} | "
            f"{_escape_md_cell(row.get('confidence_summary', '-'))} | {_escape_md_cell(row.get('source_lineage_summary', '-'))} | "
            f"{_escape_md_cell(row.get('best_reason', ''))} | {_escape_md_cell(row.get('note', ''))} |"
        )

    if group_top_rows:
        lines.append("")
        lines.append(f"## 4) 各方法论 Top{per_group_top_n} 机会池")
        lines.append("")
        for profile, rows in group_top_rows:
            lines.append(f"### {profile.name}")
            lines.append("")
            lines.append("| 排名 | 代码 | 公司 | 行业 | 组内分 | 机会验真 | 估值联动 | 风险提示 | 可信度 | 来源摘要 | 理由 | 原始备注 |")
            lines.append("|---|---|---|---|---:|---|---|---|---|---|---|---|")
            for idx, row in enumerate(rows, start=1):
                lines.append(
                    f"| {idx} | {_escape_md_cell(row.get('ticker', ''))} | {_escape_md_cell(row.get('name', ''))} | "
                    f"{_escape_md_cell(row.get('sector', ''))} | {row.get('group_score', 0.0):.2f} | "
                    f"{_escape_md_cell(build_validation_summary(row))} | {_escape_md_cell(build_valuation_summary(row))} | "
                    f"{_escape_md_cell(build_risk_summary(row))} | {_escape_md_cell(row.get('confidence_summary', '-'))} | "
                    f"{_escape_md_cell(row.get('source_lineage_summary', '-'))} | {_escape_md_cell(row.get('reason', ''))} | "
                    f"{_escape_md_cell(row.get('note', ''))} |"
                )
            lines.append("")

    if diversified_rows:
        lines.append(f"## 5) 行业分散约束版 TOP10（单行业最多 {max_per_sector} 个）")
        lines.append("")
        lines.append("| 排名 | 代码 | 公司 | 行业 | 组合分 | 最匹配方法论 | 机会验真 | 估值联动 | 风险提示 | 可信度 | 来源摘要 | 原始理由 | 原始备注 |")
        lines.append("|---|---|---|---|---:|---|---|---|---|---|---|---|---|")
        for idx, row in enumerate(diversified_rows, start=1):
            lines.append(
                f"| {idx} | {_escape_md_cell(row.get('ticker', ''))} | {_escape_md_cell(row.get('name', ''))} | "
                f"{_escape_md_cell(row.get('sector', ''))} | {row.get('composite_score', 0.0):.2f} | "
                f"{_escape_md_cell(row.get('best_group', ''))} | {_escape_md_cell(build_validation_summary(row))} | "
                f"{_escape_md_cell(build_valuation_summary(row))} | {_escape_md_cell(build_risk_summary(row))} | "
                f"{_escape_md_cell(row.get('confidence_summary', '-'))} | {_escape_md_cell(row.get('source_lineage_summary', '-'))} | "
                f"{_escape_md_cell(row.get('best_reason', ''))} | {_escape_md_cell(row.get('note', ''))} |"
            )

    lines.append("")
    lines.append("## 6) 安全边际口径参照")
    lines.append("")
    lines.append("- 项目主口径：`MOS_FV = (FV - P) / FV = 1 - P/FV`（分母为 FV，保留负值）。")
    lines.append("- 常见目标价口径：`UPSIDE_P = (FV - P) / P = FV/P - 1`（分母为现价 P）。")
    lines.append("- 口径换算：`UPSIDE_P = MOS_FV / (1 - MOS_FV)`；`MOS_FV = UPSIDE_P / (1 + UPSIDE_P)`。")
    lines.append("- Yahoo 参照：页面常见 `1y Target Est`（分析师一年目标价），通常按 `UPSIDE_P` 解读。")
    lines.append("- Morningstar 参照：常见 `Price/Fair Value`；折价口径可写为 `1 - Price/Fair Value`。")
    lines.append("- 详细来源与说明：`docs/margin_of_safety_references.md`。")

    return "\n".join(lines)
