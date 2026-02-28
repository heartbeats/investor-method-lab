#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.scoring import load_opportunities
from investor_method_lab.top20_pack import (
    build_group_profiles,
    rank_first_batch_opportunities,
    rank_opportunities_for_each_group,
    rank_diversified_opportunities,
    render_opportunity_pack_markdown,
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_group_csv(
    path: Path, rows_by_group: List[tuple[Any, List[Dict[str, Any]]]]
) -> None:
    fieldnames = [
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for profile, rows in rows_by_group:
            for idx, row in enumerate(rows, start=1):
                writer.writerow(
                    {
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
                )


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
    parser.add_argument("--top", type=int, default=10, help="输出 TOP N")
    parser.add_argument(
        "--per-group-top", type=int, default=5, help="每个方法论分组输出 TOP N"
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
        help="输出分组 TopN CSV",
    )
    parser.add_argument(
        "--output-diversified-csv",
        type=Path,
        default=PROJECT_ROOT / "output" / "top20_diversified_opportunities.csv",
        help="输出行业分散约束版 CSV",
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
        as_of_date=args.as_of_date or verified.get("as_of_date", ""),
        profiles=profiles,
        top_rows=top_rows,
        group_top_rows=group_top_rows,
        diversified_rows=diversified_rows,
        per_group_top_n=args.per_group_top,
        max_per_sector=args.max_per_sector,
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(report, encoding="utf-8")

    print(f"方法论分组数: {len(profiles)}")
    print(f"机会池输出: {args.output_csv}")
    print(f"分组机会池输出: {args.output_group_csv}")
    print(f"行业分散机会池输出: {args.output_diversified_csv}")
    print(f"报告输出: {args.output_md}")


if __name__ == "__main__":
    main()
