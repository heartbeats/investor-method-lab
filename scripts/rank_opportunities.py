#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.scoring import load_json, load_opportunities, rank_opportunities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按策略筛选机会池")
    parser.add_argument("--strategy", required=True, help="方法论 ID，例如 value_quality")
    parser.add_argument("--top", type=int, default=10, help="输出前 N 个机会")
    parser.add_argument("--min-score", type=float, default=0.0, help="最低分阈值（0-100）")
    parser.add_argument(
        "--opportunities-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.sample.csv",
        help="候选池 CSV 文件",
    )
    parser.add_argument(
        "--methodologies-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "methodologies.json",
        help="方法论文件",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=None,
        help="输出路径前缀（默认写入 output/）",
    )
    return parser.parse_args()


def get_output_prefix(prefix: Path | None, strategy_id: str) -> Path:
    if prefix is not None:
        prefix.parent.mkdir(parents=True, exist_ok=True)
        return prefix

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"opportunities_{strategy_id}_{timestamp}"


def find_strategy(strategies: list[dict], strategy_id: str) -> dict:
    for strategy in strategies:
        if strategy.get("id") == strategy_id:
            return strategy
    available = ", ".join(item.get("id", "") for item in strategies)
    raise ValueError(f"未知策略 {strategy_id}，可选：{available}")


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "ticker",
        "name",
        "sector",
        "score",
        "margin_of_safety",
        "risk_control",
        "reason",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def render_markdown(strategy: dict, rows: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"# 机会池评分报告 - {strategy['id']}（{strategy['name']}）")
    lines.append("")
    lines.append(f"核心问题：{strategy['core_question']}")
    lines.append("")
    lines.append("## Top Opportunities")
    lines.append("")

    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"{idx}. {row['ticker']} {row['name']} | 得分 {row['score']:.2f} | "
            f"安全边际 {row['margin_of_safety']:.1f} | 风控 {row['risk_control']:.1f} | "
            f"理由 {row['reason']}"
        )

    lines.append("")
    lines.append("## 筛选规则")
    lines.append("")
    for rule in strategy.get("screening_rules", []):
        lines.append(f"- {rule}")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    methodology_doc = load_json(args.methodologies_file)
    opportunities = load_opportunities(args.opportunities_file)
    strategies = methodology_doc.get("strategies", [])

    strategy = find_strategy(strategies, args.strategy)
    ranked = rank_opportunities(
        opportunities=opportunities,
        strategy=strategy,
        top_n=args.top,
        min_score=args.min_score,
    )

    print(f"Strategy: {strategy['id']} ({strategy['name']})")
    for index, row in enumerate(ranked, start=1):
        print(
            f"{index:>2}. {row['ticker']:<8} {row['name']:<20} score={row['score']:.2f} reason={row['reason']}"
        )

    prefix = get_output_prefix(args.output_prefix, args.strategy)
    csv_path = Path(f"{prefix}.csv")
    md_path = Path(f"{prefix}.md")

    write_csv(csv_path, ranked)
    md_path.write_text(render_markdown(strategy, ranked), encoding="utf-8")

    print(f"\nCSV 已写入: {csv_path}")
    print(f"报告已写入: {md_path}")


if __name__ == "__main__":
    main()
