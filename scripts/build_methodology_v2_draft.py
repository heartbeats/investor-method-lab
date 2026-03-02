#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "investor_profiles.json"
DEFAULT_TAXONOMY = PROJECT_ROOT / "data" / "methodology_taxonomy_v2.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "investor_methodology_v2_draft.json"

BUCKET_TO_FAMILY: Dict[str, str] = {
    "价值质量复利": "value_quality_compound",
    "价值+质量长期复利": "value_quality_compound",
    "高质量集中投资": "value_quality_compound",
    "行业价值": "value_quality_compound",
    "GARP": "garp_growth",
    "GARP 成长": "garp_growth",
    "深度价值": "deep_value_distress",
    "深度价值分散": "deep_value_distress",
    "绝对收益价值": "deep_value_distress",
    "信用周期/困境债": "deep_value_distress",
    "事件驱动": "event_driven_special_situations",
    "事件驱动+基本面": "event_driven_special_situations",
    "激进主义+集中持股": "event_driven_special_situations",
    "多策略套利": "event_driven_special_situations",
    "交易型宏观/事件驱动": "macro_trend",
    "宏观CTA": "macro_trend",
    "全球宏观+反身性": "macro_trend",
    "宏观+趋势+集中仓位": "macro_trend",
    "宏观趋势交易": "macro_trend",
    "趋势交易": "macro_trend",
    "系统化价值+特殊情境": "systematic_quant",
    "量化统计套利": "systematic_quant",
    "高成长主题": "thematic_growth",
    "股票多空/高周转": "equity_long_short_trading",
    "管理层持股跟踪": "disclosure_tracking",
    "披露跟踪": "disclosure_tracking",
}

ID_TO_FAMILY_OVERRIDE: Dict[str, str] = {
    "steven_cohen": "equity_long_short_trading",
    "jensen_huang": "disclosure_tracking",
}

FAMILY_DEFAULT_TAGS: Dict[str, List[str]] = {
    "value_quality_compound": ["长期持有", "基本面主导", "集中持仓"],
    "garp_growth": ["长期持有", "基本面主导"],
    "deep_value_distress": ["基本面主导", "事件催化"],
    "event_driven_special_situations": ["事件催化", "基本面主导"],
    "macro_trend": ["宏观自上而下", "趋势跟随"],
    "systematic_quant": ["系统化规则", "分散组合"],
    "thematic_growth": ["主题进攻", "集中持仓"],
    "equity_long_short_trading": ["高换手", "多空对冲", "基本面主导"],
    "disclosure_tracking": ["披露行为跟踪"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成方法论V2分类草案")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT, help="输入 investor_profiles.json")
    parser.add_argument("--taxonomy-file", type=Path, default=DEFAULT_TAXONOMY, help="输入 methodology_taxonomy_v2.json")
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT, help="输出 investor_methodology_v2_draft.json")
    return parser.parse_args()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _pick_family(item: Dict[str, Any]) -> Tuple[str, str, str]:
    investor_id = str(item.get("id") or "")
    role_type = str(item.get("role_type") or "")
    bucket = str(item.get("methodology_bucket") or "")

    if investor_id in ID_TO_FAMILY_OVERRIDE:
        return ID_TO_FAMILY_OVERRIDE[investor_id], "medium", "id_override"

    if bucket in BUCKET_TO_FAMILY:
        return BUCKET_TO_FAMILY[bucket], "high", "bucket_mapping"

    if role_type in {"politician_disclosure", "insider"}:
        return "disclosure_tracking", "medium", "role_fallback_disclosure"
    if role_type == "fund_manager":
        return "thematic_growth", "medium", "role_fallback_fund_manager"
    if role_type == "public_figure":
        return "event_driven_special_situations", "medium", "role_fallback_public_figure"

    return "value_quality_compound", "low", "default_fallback"


def _execution_tags(item: Dict[str, Any], family_id: str) -> List[str]:
    role_type = str(item.get("role_type") or "")
    bucket = str(item.get("methodology_bucket") or "")
    tags = list(FAMILY_DEFAULT_TAGS.get(family_id, []))

    if "集中" in bucket and "集中持仓" not in tags:
        tags.append("集中持仓")
    if "分散" in bucket and "分散组合" not in tags:
        tags.append("分散组合")
    if "趋势" in bucket and "趋势跟随" not in tags:
        tags.append("趋势跟随")
    if "事件" in bucket and "事件催化" not in tags:
        tags.append("事件催化")
    if "行业" in bucket and "行业深耕" not in tags:
        tags.append("行业深耕")
    if "高周转" in bucket and "高换手" not in tags:
        tags.append("高换手")
    if "股票多空" in bucket and "多空对冲" not in tags:
        tags.append("多空对冲")
    if "信用" in bucket and "困境信用" not in tags:
        tags.append("困境信用")

    if role_type == "insider" and "管理层行为跟踪" not in tags:
        tags.append("管理层行为跟踪")
    if role_type in {"politician_disclosure", "public_figure"} and "披露行为跟踪" not in tags:
        tags.append("披露行为跟踪")

    return list(dict.fromkeys(tags))


def _disclosure_tags(item: Dict[str, Any]) -> List[str]:
    role_type = str(item.get("role_type") or "")
    futu_status = str(item.get("futu_alignment_status") or "")
    source_refs = item.get("source_refs") or []
    return_basis = str(item.get("return_basis") or "")

    tags: List[str] = []

    calibrated = item.get("calibrated_return_pct")
    if _is_number(calibrated) and "not_publicly_audited" not in return_basis:
        tags.append("可审计历史收益")

    if _is_number(item.get("annualized_return_proxy_pct")):
        tags.append("13F代理收益")

    if futu_status in {"ready_for_futu_compare", "pending_futu_runtime", "partial_direct_plus_lookthrough"}:
        tags.append("13F可核验")

    if role_type == "insider":
        tags.append("管理层持股披露")
        tags.append("非完整组合披露")
    if role_type == "politician_disclosure":
        tags.append("议员交易披露")
        tags.append("非完整组合披露")
    if role_type == "public_figure":
        tags.append("公开资料推断")
        tags.append("非完整组合披露")

    if futu_status == "not_applicable_complete_portfolio":
        tags.append("非完整组合披露")

    if "public_interviews_and_reports" in source_refs:
        tags.append("公开资料推断")

    if not tags:
        tags.append("公开资料推断")

    return list(dict.fromkeys(tags))


def build(payload: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    family_map = {
        str(item.get("id") or ""): str(item.get("name") or "")
        for item in taxonomy.get("strategy_families", [])
        if isinstance(item, dict)
    }

    mapped: List[Dict[str, Any]] = []
    for item in payload.get("investors", []):
        if not isinstance(item, dict):
            continue
        family_id, confidence, by = _pick_family(item)
        mapped.append(
            {
                "id": item.get("id"),
                "name_cn": item.get("name_cn"),
                "name_en": item.get("name_en"),
                "role_type": item.get("role_type"),
                "legacy_methodology_bucket": item.get("methodology_bucket"),
                "primary_family_id": family_id,
                "primary_family_name": family_map.get(family_id, family_id),
                "execution_tags": _execution_tags(item, family_id),
                "disclosure_tags": _disclosure_tags(item),
                "mapping_confidence": confidence,
                "mapping_by": by,
                "mapping_note": "V2草案映射：用于统一分类口径，后续可人工微调。",
            }
        )

    family_counts = Counter(str(item.get("primary_family_id") or "") for item in mapped)
    role_counts = Counter(str(item.get("role_type") or "") for item in mapped)
    confidence_counts = Counter(str(item.get("mapping_confidence") or "") for item in mapped)

    return {
        "version": str(taxonomy.get("version") or "v2-draft"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investor_count": len(mapped),
        "summary": {
            "family_counts": dict(sorted(family_counts.items(), key=lambda x: (-x[1], x[0]))),
            "role_counts": dict(sorted(role_counts.items(), key=lambda x: (-x[1], x[0]))),
            "mapping_confidence_counts": dict(sorted(confidence_counts.items(), key=lambda x: (-x[1], x[0]))),
        },
        "investors": mapped,
        "notes": [
            "本文件是方法论V2分类草案，尚未替换线上筛选逻辑。",
            "分类结构为：1个主策略家族 + 多个执行标签 + 多个披露口径标签。",
        ],
    }


def main() -> None:
    args = parse_args()
    payload = _load_json(args.input_file)
    taxonomy = _load_json(args.taxonomy_file)
    output = build(payload, taxonomy)
    args.output_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"methodology v2 draft generated: {args.output_file}")
    print(f"investor_count: {output.get('investor_count')}")
    print(f"family_counts: {output.get('summary', {}).get('family_counts', {})}")


if __name__ == "__main__":
    main()
