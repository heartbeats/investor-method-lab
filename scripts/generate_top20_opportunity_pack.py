#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.scoring import load_opportunities
from investor_method_lab.top20_pack import (
    build_group_profiles,
    rank_diversified_opportunities,
    rank_first_batch_opportunities,
    rank_opportunities_for_each_group,
    render_opportunity_pack_markdown,
)
from investor_method_lab.top20_pack_v4 import (
    build_v4_analysis,
    load_rulebook,
    render_methodology_playbook_v4,
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _to_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _resolve_extra_fieldnames(
    rows: Iterable[Dict[str, Any]],
    base_fields: List[str],
    preferred: List[str],
) -> List[str]:
    present = set()
    for row in rows:
        for key in row.keys():
            if key not in base_fields:
                present.add(key)
    return [key for key in preferred if key in present and key not in base_fields]


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    base_fields = [
        "ticker",
        "name",
        "sector",
        "composite_score",
        "best_group",
        "best_reason",
        "margin_of_safety",
        "risk_control",
        "note",
    ]
    preferred_extras = [
        "market",
        "market_norm_margin_of_safety",
        "market_norm_quality",
        "market_norm_growth",
        "market_norm_momentum",
        "market_norm_catalyst",
        "market_norm_risk_control",
        "explain_best_group_id",
        "explain_best_group_weighted_contribution",
        "explain_passed_group_count",
        "explain_failed_group_count",
        "explain_market",
        "explain_group_trace_json",
    ]
    fieldnames = base_fields + _resolve_extra_fieldnames(rows, base_fields, preferred_extras)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _to_cell(row.get(key, "")) for key in fieldnames})


def write_group_csv(path: Path, rows_by_group: List[Tuple[Any, List[Dict[str, Any]]]]) -> None:
    base_fields = [
        "group_id",
        "group_name",
        "group_rank",
        "ticker",
        "name",
        "sector",
        "group_score",
        "reason",
        "margin_of_safety",
        "risk_control",
        "note",
    ]
    candidate_rows = [row for _, rows in rows_by_group for row in rows]
    preferred_extras = [
        "tier",
        "base_score",
        "penalty_multiplier",
        "hard_pass",
        "hard_fail_reasons",
        "soft_penalties",
        "market",
        "market_norm_margin_of_safety",
        "market_norm_quality",
        "market_norm_growth",
        "market_norm_momentum",
        "market_norm_catalyst",
        "market_norm_risk_control",
        "trace_id",
    ]
    fieldnames = base_fields + _resolve_extra_fieldnames(candidate_rows, base_fields, preferred_extras)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for profile, rows in rows_by_group:
            for idx, row in enumerate(rows, start=1):
                payload = {
                    "group_id": getattr(profile, "id", ""),
                    "group_name": getattr(profile, "name", ""),
                    "group_rank": idx,
                    "ticker": row.get("ticker", ""),
                    "name": row.get("name", ""),
                    "sector": row.get("sector", ""),
                    "group_score": row.get("group_score", ""),
                    "reason": row.get("reason", ""),
                    "margin_of_safety": row.get("margin_of_safety", ""),
                    "risk_control": row.get("risk_control", ""),
                    "note": row.get("note", ""),
                }
                for key in fieldnames:
                    if key in payload:
                        continue
                    payload[key] = row.get(key, "")
                writer.writerow({key: _to_cell(payload.get(key, "")) for key in fieldnames})


def write_tiered_group_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "group_id",
        "group_name",
        "tier",
        "group_rank",
        "ticker",
        "name",
        "sector",
        "market",
        "group_score",
        "base_score",
        "penalty_multiplier",
        "hard_pass",
        "hard_fail_reasons",
        "soft_penalties",
        "reason",
        "margin_of_safety",
        "risk_control",
        "market_norm_margin_of_safety",
        "market_norm_quality",
        "market_norm_growth",
        "market_norm_momentum",
        "market_norm_catalyst",
        "market_norm_risk_control",
        "note",
        "trace_id",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _to_cell(row.get(key, "")) for key in fieldnames})


def write_decision_trace_json(
    path: Path,
    *,
    as_of_date: str,
    rulebook_version: str,
    rows: List[Dict[str, Any]],
) -> None:
    payload = {
        "version": "v4",
        "rulebook_version": rulebook_version,
        "as_of_date": as_of_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 Top20 方法论机会包")
    parser.add_argument(
        "--verified-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_verified_ab.json",
        help="Top20 可审计样本文件（A/B）",
    )
    parser.add_argument(
        "--framework-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_methodology_framework.json",
        help="Top20 方法论分组映射",
    )
    parser.add_argument(
        "--methodologies-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "methodologies.json",
        help="方法论基础权重文件",
    )
    parser.add_argument(
        "--opportunities-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.sample.csv",
        help="候选池文件",
    )
    parser.add_argument(
        "--engine-version",
        choices=["legacy", "v4"],
        default="v4",
        help="执行引擎版本（默认 v4）",
    )
    parser.add_argument(
        "--rulebook-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "methodology_rulebook_v4.json",
        help="V4 方法论规则文件",
    )
    parser.add_argument("--top", type=int, default=10, help="输出 TOP N")
    parser.add_argument(
        "--per-group-top", type=int, default=5, help="每个方法论分组输出 TOP N"
    )
    parser.add_argument(
        "--per-tier-top",
        type=int,
        default=10,
        help="V4 每个方法论分组在每层池输出 TOP N",
    )
    parser.add_argument(
        "--max-per-sector", type=int, default=2, help="行业分散版每个行业最多保留数量"
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "output" / "top20_first_batch_opportunities.csv",
        help="输出 CSV",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "top20_opportunity_pack.md",
        help="输出 Markdown 报告",
    )
    parser.add_argument(
        "--output-group-csv",
        type=Path,
        default=PROJECT_ROOT / "output" / "top20_methodology_top5_by_group.csv",
        help="输出分组 TopN CSV（兼容旧契约）",
    )
    parser.add_argument(
        "--output-diversified-csv",
        type=Path,
        default=PROJECT_ROOT / "output" / "top20_diversified_opportunities.csv",
        help="输出行业分散约束版 CSV",
    )
    parser.add_argument(
        "--output-tiered-group-csv",
        type=Path,
        default=PROJECT_ROOT / "output" / "top20_methodology_top10_by_group_tiered.csv",
        help="V4 分层分组输出 CSV",
    )
    parser.add_argument(
        "--output-decision-trace-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "method_decision_trace.json",
        help="V4 决策轨迹输出 JSON",
    )
    parser.add_argument(
        "--output-playbook-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "methodology_playbook_v4.md",
        help="V4 方法卡文档输出",
    )
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="报告日期覆盖（例如 2026-02-28）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    verified = load_json(args.verified_file)
    framework = load_json(args.framework_file)
    methodologies = load_json(args.methodologies_file)
    opportunities = load_opportunities(args.opportunities_file)

    profiles = build_group_profiles(
        investors=verified.get("investors", []),
        framework=framework,
        strategies=methodologies.get("strategies", []),
    )
    if not profiles:
        raise ValueError("No group profiles built. Check framework mapping and verified universe.")

    as_of_date = args.as_of_date or verified.get("as_of_date", "")

    if args.engine_version == "v4":
        if not args.rulebook_file.exists():
            raise FileNotFoundError(f"rulebook not found: {args.rulebook_file}")
        rulebook = load_rulebook(args.rulebook_file)
        analysis = build_v4_analysis(
            opportunities,
            profiles,
            rulebook,
            top_n=args.top,
            max_per_sector=args.max_per_sector,
            per_group_top_n=args.per_group_top,
            per_tier_top_n=args.per_tier_top,
        )

        top_rows = analysis["top_rows"]
        group_top_rows = analysis["group_top_rows"]
        diversified_rows = analysis["diversified_rows"]
        tiered_group_rows = analysis["tiered_group_rows"]
        decision_trace_rows = analysis["decision_trace_rows"]

        write_csv(args.output_csv, top_rows)
        write_group_csv(args.output_group_csv, group_top_rows)
        write_csv(args.output_diversified_csv, diversified_rows)
        write_tiered_group_csv(args.output_tiered_group_csv, tiered_group_rows)
        write_decision_trace_json(
            args.output_decision_trace_json,
            as_of_date=as_of_date,
            rulebook_version=str(rulebook.get("version", "v4")),
            rows=decision_trace_rows,
        )

        playbook = render_methodology_playbook_v4(
            as_of_date=as_of_date,
            profiles=profiles,
            rulebook=rulebook,
            group_stats=analysis.get("group_stats", {}),
        )
        args.output_playbook_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_playbook_md.write_text(playbook, encoding="utf-8")
    else:
        top_rows = rank_first_batch_opportunities(opportunities, profiles, top_n=args.top)
        group_top_rows = rank_opportunities_for_each_group(
            opportunities, profiles, top_n_per_group=args.per_group_top
        )
        diversified_rows = rank_diversified_opportunities(
            opportunities,
            profiles,
            top_n=args.top,
            max_per_sector=args.max_per_sector,
        )
        write_csv(args.output_csv, top_rows)
        write_group_csv(args.output_group_csv, group_top_rows)
        write_csv(args.output_diversified_csv, diversified_rows)

    report = render_opportunity_pack_markdown(
        as_of_date=as_of_date,
        profiles=profiles,
        top_rows=top_rows,
        group_top_rows=group_top_rows,
        diversified_rows=diversified_rows,
        per_group_top_n=args.per_group_top,
        max_per_sector=args.max_per_sector,
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report, encoding="utf-8")

    print(f"引擎版本: {args.engine_version}")
    print(f"方法论分组数: {len(profiles)}")
    print(f"机会池输出: {args.output_csv}")
    print(f"分组机会池输出: {args.output_group_csv}")
    print(f"行业分散机会池输出: {args.output_diversified_csv}")
    if args.engine_version == "v4":
        print(f"分层机会池输出: {args.output_tiered_group_csv}")
        print(f"决策轨迹输出: {args.output_decision_trace_json}")
        print(f"方法卡输出: {args.output_playbook_md}")
    print(f"报告输出: {args.output_md}")


if __name__ == "__main__":
    main()
