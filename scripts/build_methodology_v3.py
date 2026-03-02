#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "investor_profiles.json"
DEFAULT_TAXONOMY = PROJECT_ROOT / "data" / "methodology_taxonomy_v3.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "investor_methodology_v3.json"


MANUAL_MAP: Dict[str, Dict[str, Any]] = {
    "peter_brandt": {
        "track_id": "investment_method",
        "primary_family_id": "trend_following",
        "secondary_family_ids": [],
        "execution_tags": ["趋势跟随", "高换手", "纪律止损", "短线交易"],
        "mapping_confidence": "high",
        "mapping_note": "交易体系以技术形态与止损纪律为核心，归入纯趋势。",
    },
    "duan_yongping": {
        "track_id": "investment_method",
        "primary_family_id": "quality_value_compounding",
        "secondary_family_ids": [],
        "execution_tags": ["长期持有", "基本面主导", "集中持仓", "低换手"],
        "mapping_confidence": "high",
        "mapping_note": "强调能力圈、商业模式与长期复利。",
    },
    "joel_greenblatt": {
        "track_id": "investment_method",
        "primary_family_id": "systematic_value_factors",
        "secondary_family_ids": ["event_driven_special_situations"],
        "execution_tags": ["系统化规则", "基本面主导", "分散组合", "中线波段"],
        "mapping_confidence": "high",
        "mapping_note": "主框架为规则化价值因子，兼有特殊情境偏好。",
    },
    "li_lu": {
        "track_id": "investment_method",
        "primary_family_id": "quality_value_compounding",
        "secondary_family_ids": [],
        "execution_tags": ["长期持有", "基本面主导", "集中持仓", "低换手"],
        "mapping_confidence": "high",
        "mapping_note": "安全边际+长期赔率，核心是高质量价值复利。",
    },
    "james_simons": {
        "track_id": "investment_method",
        "primary_family_id": "quant_stat_arb",
        "secondary_family_ids": [],
        "execution_tags": ["系统化规则", "多空对冲", "高换手", "分散组合"],
        "mapping_confidence": "high",
        "mapping_note": "典型统计套利与市场中性组合。",
    },
    "bruce_kovner": {
        "track_id": "investment_method",
        "primary_family_id": "macro_discretionary",
        "secondary_family_ids": ["trend_following"],
        "execution_tags": ["宏观自上而下", "趋势跟随", "纪律止损", "中线波段"],
        "mapping_confidence": "high",
        "mapping_note": "以主观宏观为核心，执行上有明显趋势与风险纪律。",
    },
    "george_soros": {
        "track_id": "investment_method",
        "primary_family_id": "macro_discretionary",
        "secondary_family_ids": ["trend_following"],
        "execution_tags": ["宏观自上而下", "趋势跟随", "集中持仓", "高换手"],
        "mapping_confidence": "high",
        "mapping_note": "核心是反身性驱动的宏观方向交易。",
    },
    "stanley_druckenmiller": {
        "track_id": "investment_method",
        "primary_family_id": "macro_discretionary",
        "secondary_family_ids": ["trend_following"],
        "execution_tags": ["宏观自上而下", "趋势跟随", "集中持仓", "高换手"],
        "mapping_confidence": "high",
        "mapping_note": "宏观判断+顺势重仓是主策略。",
    },
    "steven_cohen": {
        "track_id": "investment_method",
        "primary_family_id": "equity_long_short_trading",
        "secondary_family_ids": [],
        "execution_tags": ["多空对冲", "高换手", "基本面主导", "短线交易"],
        "mapping_confidence": "high",
        "mapping_note": "多空交易与高执行频率是核心特征。",
    },
    "peter_lynch": {
        "track_id": "investment_method",
        "primary_family_id": "garp_growth",
        "secondary_family_ids": [],
        "execution_tags": ["基本面主导", "长期持有", "分散组合", "中线波段"],
        "mapping_confidence": "high",
        "mapping_note": "典型GARP框架：增长与估值匹配。",
    },
    "paul_tudor_jones": {
        "track_id": "investment_method",
        "primary_family_id": "macro_discretionary",
        "secondary_family_ids": ["trend_following"],
        "execution_tags": ["宏观自上而下", "趋势跟随", "纪律止损", "高换手"],
        "mapping_confidence": "high",
        "mapping_note": "宏观交易框架下的趋势化执行。",
    },
    "michael_steinhardt": {
        "track_id": "investment_method",
        "primary_family_id": "macro_discretionary",
        "secondary_family_ids": ["event_driven_special_situations"],
        "execution_tags": ["宏观自上而下", "事件催化", "高换手", "中线波段"],
        "mapping_confidence": "high",
        "mapping_note": "交易型宏观为主，事件催化为辅。",
    },
    "leon_levy": {
        "track_id": "investment_method",
        "primary_family_id": "event_driven_special_situations",
        "secondary_family_ids": [],
        "execution_tags": ["事件催化", "分散组合", "基本面主导", "中线波段"],
        "mapping_confidence": "high",
        "mapping_note": "多策略套利本质属于事件/特殊情境收益。",
    },
    "shelby_davis": {
        "track_id": "investment_method",
        "primary_family_id": "industry_specialist_value",
        "secondary_family_ids": ["quality_value_compounding"],
        "execution_tags": ["行业深耕", "长期持有", "基本面主导", "集中持仓"],
        "mapping_confidence": "high",
        "mapping_note": "行业专精（保险）驱动长期复利。",
    },
    "warren_buffett": {
        "track_id": "investment_method",
        "primary_family_id": "quality_value_compounding",
        "secondary_family_ids": [],
        "execution_tags": ["长期持有", "基本面主导", "集中持仓", "低换手"],
        "mapping_confidence": "high",
        "mapping_note": "价值质量复利的典型代表。",
    },
    "charlie_munger": {
        "track_id": "investment_method",
        "primary_family_id": "quality_value_compounding",
        "secondary_family_ids": [],
        "execution_tags": ["长期持有", "基本面主导", "集中持仓", "低换手"],
        "mapping_confidence": "high",
        "mapping_note": "好公司+合理价格，集中长期持有。",
    },
    "seth_klarman": {
        "track_id": "investment_method",
        "primary_family_id": "deep_value_distress",
        "secondary_family_ids": [],
        "execution_tags": ["基本面主导", "分散组合", "低换手", "困境信用"],
        "mapping_confidence": "high",
        "mapping_note": "绝对收益价值与下行保护优先。",
    },
    "bill_ackman": {
        "track_id": "investment_method",
        "primary_family_id": "event_driven_special_situations",
        "secondary_family_ids": [],
        "execution_tags": ["激进主义", "事件催化", "集中持仓", "基本面主导"],
        "mapping_confidence": "high",
        "mapping_note": "激进主义与治理催化是核心方法。",
    },
    "howard_marks": {
        "track_id": "investment_method",
        "primary_family_id": "deep_value_distress",
        "secondary_family_ids": ["macro_discretionary"],
        "execution_tags": ["困境信用", "基本面主导", "分散组合", "宏观自上而下"],
        "mapping_confidence": "high",
        "mapping_note": "信用周期与困境资产投资为主。",
    },
    "walter_schloss": {
        "track_id": "investment_method",
        "primary_family_id": "deep_value_distress",
        "secondary_family_ids": [],
        "execution_tags": ["分散组合", "基本面主导", "低换手", "长期持有"],
        "mapping_confidence": "high",
        "mapping_note": "深度价值分散，弱催化依赖。",
    },
    "mohnish_pabrai": {
        "track_id": "investment_method",
        "primary_family_id": "deep_value_distress",
        "secondary_family_ids": [],
        "execution_tags": ["集中持仓", "基本面主导", "低换手", "长期持有"],
        "mapping_confidence": "high",
        "mapping_note": "低风险高不对称下注，深度价值风格。",
    },
    "dan_loeb": {
        "track_id": "investment_method",
        "primary_family_id": "event_driven_special_situations",
        "secondary_family_ids": [],
        "execution_tags": ["事件催化", "激进主义", "集中持仓", "基本面主导"],
        "mapping_confidence": "high",
        "mapping_note": "事件催化与激进主义组合打法。",
    },
    "cathie_wood": {
        "track_id": "investment_method",
        "primary_family_id": "thematic_innovation_growth",
        "secondary_family_ids": [],
        "execution_tags": ["主题进攻", "集中持仓", "高换手", "基本面主导"],
        "mapping_confidence": "high",
        "mapping_note": "以创新主题和高成长假设驱动配置。",
    },
    "jensen_huang": {
        "track_id": "disclosure_observation",
        "primary_family_id": "insider_exposure_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪", "管理层行为跟踪"],
        "mapping_confidence": "high",
        "mapping_note": "主体信息主要来自管理层持股与关联披露。",
    },
    "josh_gottheimer": {
        "track_id": "disclosure_observation",
        "primary_family_id": "congressional_disclosure_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪"],
        "mapping_confidence": "high",
        "mapping_note": "议员交易披露口径，非完整组合。",
    },
    "nancy_pelosi": {
        "track_id": "disclosure_observation",
        "primary_family_id": "congressional_disclosure_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪"],
        "mapping_confidence": "high",
        "mapping_note": "议员交易披露口径，非完整组合。",
    },
    "gil_cisneros": {
        "track_id": "disclosure_observation",
        "primary_family_id": "congressional_disclosure_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪"],
        "mapping_confidence": "high",
        "mapping_note": "议员交易披露口径，非完整组合。",
    },
    "marjorie_taylor_greene": {
        "track_id": "disclosure_observation",
        "primary_family_id": "congressional_disclosure_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪"],
        "mapping_confidence": "high",
        "mapping_note": "议员交易披露口径，非完整组合。",
    },
    "donald_trump": {
        "track_id": "disclosure_observation",
        "primary_family_id": "public_figure_asset_event_tracking",
        "secondary_family_ids": [],
        "execution_tags": ["披露行为跟踪", "事件催化"],
        "mapping_confidence": "high",
        "mapping_note": "公开资料与关联资产事件跟踪，不等同投资组合策略。",
    },
}


AUDITED_NET_RETURN_BASIS = {
    "net",
    "net_annualized",
    "annualized_after_fees",
    "net_after_performance_fee",
    "net_irr_since_inception_opportunistic_credit",
}

FUTU_13F_STATUS = {"ready_for_futu_compare", "pending_futu_runtime", "partial_direct_plus_lookthrough"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成方法论V3分类结果")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT, help="输入 investor_profiles.json")
    parser.add_argument("--taxonomy-file", type=Path, default=DEFAULT_TAXONOMY, help="输入 methodology_taxonomy_v3.json")
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT, help="输出 investor_methodology_v3.json")
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def build_disclosure_tags(item: Dict[str, Any]) -> List[str]:
    tags: List[str] = []

    role_type = str(item.get("role_type") or "")
    return_basis = str(item.get("return_basis") or "")
    futu_status = str(item.get("futu_alignment_status") or "")
    source_refs = set(str(x) for x in (item.get("source_refs") or []))

    if return_basis in AUDITED_NET_RETURN_BASIS:
        tags.append("收益可核验(净口径)")
    elif is_number(item.get("calibrated_return_pct")):
        tags.append("公开资料收益口径")

    if is_number(item.get("annualized_return_proxy_pct")):
        tags.append("13F代理收益")

    if futu_status in FUTU_13F_STATUS:
        tags.append("13F持仓可核验")

    if role_type == "insider":
        tags.extend(["管理层持股披露", "非完整组合披露"])
    elif role_type == "politician_disclosure":
        tags.extend(["议员交易披露", "非完整组合披露"])
    elif role_type == "public_figure":
        tags.extend(["公开资料推断", "非完整组合披露"])

    if futu_status == "not_applicable_complete_portfolio" and "非完整组合披露" not in tags:
        tags.append("非完整组合披露")

    if "public_interviews_and_reports" in source_refs and "公开资料推断" not in tags:
        tags.append("公开资料推断")

    if not tags:
        tags.append("公开资料推断")

    return list(dict.fromkeys(tags))


def get_track_name(taxonomy: Dict[str, Any], track_id: str) -> str:
    for item in taxonomy.get("tracks", []):
        if str(item.get("id") or "") == track_id:
            return str(item.get("name") or track_id)
    return track_id


def get_family_name(taxonomy: Dict[str, Any], family_id: str) -> str:
    for item in taxonomy.get("families", []):
        if str(item.get("id") or "") == family_id:
            return str(item.get("name") or family_id)
    return family_id


def validate_catalog(taxonomy: Dict[str, Any], mapped: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    family_ids = {str(item.get("id") or "") for item in taxonomy.get("families", [])}
    track_ids = {str(item.get("id") or "") for item in taxonomy.get("tracks", [])}
    exec_tags = {str(x) for x in taxonomy.get("execution_tag_catalog", [])}
    disclosure_tags = {str(x) for x in taxonomy.get("disclosure_tag_catalog", [])}

    for item in mapped:
        if item["track_id"] not in track_ids:
            issues.append(f"unknown track_id for {item['id']}: {item['track_id']}")
        if item["primary_family_id"] not in family_ids:
            issues.append(f"unknown primary_family_id for {item['id']}: {item['primary_family_id']}")
        for fid in item.get("secondary_family_ids", []):
            if fid not in family_ids:
                issues.append(f"unknown secondary_family_id for {item['id']}: {fid}")
        for tag in item.get("execution_tags", []):
            if tag not in exec_tags:
                issues.append(f"unknown execution tag for {item['id']}: {tag}")
        for tag in item.get("disclosure_tags", []):
            if tag not in disclosure_tags:
                issues.append(f"unknown disclosure tag for {item['id']}: {tag}")

    return issues


def build(payload: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    investors = [item for item in payload.get("investors", []) if isinstance(item, dict)]

    output_rows: List[Dict[str, Any]] = []
    for item in investors:
        investor_id = str(item.get("id") or "")
        mapping = MANUAL_MAP.get(investor_id)
        if mapping is None:
            role = str(item.get("role_type") or "")
            if role in {"insider", "politician_disclosure", "public_figure"}:
                mapping = {
                    "track_id": "disclosure_observation",
                    "primary_family_id": "public_figure_asset_event_tracking",
                    "secondary_family_ids": [],
                    "execution_tags": ["披露行为跟踪"],
                    "mapping_confidence": "low",
                    "mapping_note": "未在手工映射表命中，按角色回退。",
                }
            else:
                mapping = {
                    "track_id": "investment_method",
                    "primary_family_id": "quality_value_compounding",
                    "secondary_family_ids": [],
                    "execution_tags": ["基本面主导"],
                    "mapping_confidence": "low",
                    "mapping_note": "未在手工映射表命中，按默认投资主体回退。",
                }

        disclosure_tags = build_disclosure_tags(item)
        row = {
            "id": investor_id,
            "name_cn": item.get("name_cn"),
            "name_en": item.get("name_en"),
            "role_type": item.get("role_type"),
            "legacy_methodology_bucket": item.get("methodology_bucket"),
            "track_id": mapping["track_id"],
            "track_name": get_track_name(taxonomy, mapping["track_id"]),
            "primary_family_id": mapping["primary_family_id"],
            "primary_family_name": get_family_name(taxonomy, mapping["primary_family_id"]),
            "secondary_family_ids": mapping.get("secondary_family_ids", []),
            "secondary_family_names": [get_family_name(taxonomy, fid) for fid in mapping.get("secondary_family_ids", [])],
            "execution_tags": mapping.get("execution_tags", []),
            "disclosure_tags": disclosure_tags,
            "investability": "stock_selection_eligible"
            if mapping["track_id"] == "investment_method"
            else "observation_only",
            "mapping_confidence": mapping.get("mapping_confidence", "medium"),
            "mapping_note": mapping.get("mapping_note", ""),
        }
        output_rows.append(row)

    issues = validate_catalog(taxonomy, output_rows)
    track_counts = Counter(row["track_id"] for row in output_rows)
    family_counts = Counter(row["primary_family_id"] for row in output_rows)
    confidence_counts = Counter(row["mapping_confidence"] for row in output_rows)
    investable_rows = [row for row in output_rows if row["track_id"] == "investment_method"]
    observation_rows = [row for row in output_rows if row["track_id"] == "disclosure_observation"]

    return {
        "version": str(taxonomy.get("version") or "v3"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investor_count": len(output_rows),
        "summary": {
            "track_counts": dict(sorted(track_counts.items(), key=lambda x: (-x[1], x[0]))),
            "family_counts": dict(sorted(family_counts.items(), key=lambda x: (-x[1], x[0]))),
            "mapping_confidence_counts": dict(sorted(confidence_counts.items(), key=lambda x: (-x[1], x[0]))),
            "stock_selection_eligible_count": len(investable_rows),
            "observation_only_count": len(observation_rows),
            "validation_issue_count": len(issues),
        },
        "validation_issues": issues,
        "investors": output_rows,
        "notes": [
            "V3采用手工主映射 + 规则化披露标签，优先保证分类语义稳定。",
            "披露跟踪主体默认标记为 observation_only，不混入选股主方法统计。",
            "本文件可直接作为前端三维筛选（主家族/执行标签/披露标签）数据源。",
        ],
    }


def main() -> None:
    args = parse_args()
    payload = load_json(args.input_file)
    taxonomy = load_json(args.taxonomy_file)
    result = build(payload, taxonomy)
    args.output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"methodology v3 generated: {args.output_file}")
    print(f"summary: {result.get('summary')}")
    if result.get("validation_issues"):
        print("validation issues:")
        for line in result["validation_issues"]:
            print(f"- {line}")


if __name__ == "__main__":
    main()
