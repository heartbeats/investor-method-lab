#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.investor_ranking import rank_investors
from investor_method_lab.scoring import load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="投资人综合排名")
    parser.add_argument("--top", type=int, default=10, help="输出前 N 名")
    parser.add_argument(
        "--investors-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "investors.json",
        help="投资人数据文件",
    )
    parser.add_argument(
        "--methodologies-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "methodologies.json",
        help="方法论数据文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出报告文件（默认写入 output/）",
    )
    return parser.parse_args()


def get_output_path(output: Path | None) -> Path:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        return output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = PROJECT_ROOT / "output" / f"top_investors_{timestamp}.md"
    result.parent.mkdir(parents=True, exist_ok=True)
    return result


def render_report(ranked: list[dict], strategies: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# 顶级投资人研究榜单")
    lines.append("")
    lines.append("## Top Investors")
    lines.append("")
    for index, investor in enumerate(ranked, start=1):
        methodologies = ", ".join(investor.get("methodology_ids", []))
        tags = " / ".join(investor.get("style_tags", []))
        lines.append(
            f"{index}. {investor['name']} | 综合分 {investor['score']:.2f} | 强项 {investor['reason']} | 方法论 {methodologies} | 标签 {tags}"
        )

    lines.append("")
    lines.append("## Methodology Coverage")
    lines.append("")

    by_id = {investor["id"]: investor for investor in ranked}
    for strategy in strategies:
        members = [by_id[i]["name"] for i in strategy.get("investor_ids", []) if i in by_id]
        if not members:
            continue
        joined = "、".join(members)
        lines.append(f"- {strategy['id']}（{strategy['name']}）: {joined}")

    lines.append("")
    lines.append("## 下一步")
    lines.append("")
    lines.append("- 先研究 Top 5，每人产出一页方法卡（买入条件/卖出条件/错误清单）")
    lines.append("- 用方法卡反推候选池，跑机会评分，形成每周复盘")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    investors_doc = load_json(args.investors_file)
    methodology_doc = load_json(args.methodologies_file)

    ranked = rank_investors(
        investors=investors_doc.get("investors", []),
        metric_weights=investors_doc.get("score_weights", {}),
        top_n=args.top,
    )

    print("Top Investors:")
    for index, investor in enumerate(ranked, start=1):
        print(
            f"{index:>2}. {investor['name']:<24} score={investor['score']:.2f} reason={investor['reason']}"
        )

    output_path = get_output_path(args.output)
    report = render_report(ranked, methodology_doc.get("strategies", []))
    output_path.write_text(report, encoding="utf-8")

    print(f"\n报告已写入: {output_path}")


if __name__ == "__main__":
    main()
