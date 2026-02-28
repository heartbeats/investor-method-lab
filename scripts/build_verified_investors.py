#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.verification import (
    build_verified_universe,
    render_backlog_markdown,
    render_verified_markdown,
)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建可审计投资人榜单")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_10y_plus_calibrated.json",
        help="校准数据 JSON",
    )
    parser.add_argument(
        "--min-confidence",
        default="B",
        help="最小可信度（A/B/C，默认 B）",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "data" / "top20_global_investors_verified_ab.json",
        help="输出 JSON",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "top20_global_investors_verified_ab.md",
        help="输出 Markdown 报告",
    )
    parser.add_argument(
        "--backlog-md",
        type=Path,
        default=PROJECT_ROOT / "docs" / "top20_verification_backlog.md",
        help="输出低可信度待核验清单",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_json(args.input)
    investors = data.get("investors", [])
    as_of_date = data.get("as_of_date", "")
    min_confidence = str(args.min_confidence).upper().strip()

    result = build_verified_universe(investors, min_confidence=min_confidence)

    payload = {
        "as_of_date": as_of_date,
        "min_confidence": min_confidence,
        "included_count": len(result.included),
        "excluded_count": len(result.excluded),
        "investors": result.included,
        "excluded": [
            {
                "id": item.get("id"),
                "name_cn": item.get("name_cn"),
                "name_en": item.get("name_en"),
                "confidence": item.get("confidence"),
            }
            for item in result.excluded
        ],
        "source_legend": data.get("source_legend", {}),
    }

    dump_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.backlog_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_verified_markdown(result.included, min_confidence=min_confidence, as_of_date=as_of_date),
        encoding="utf-8",
    )
    args.backlog_md.write_text(
        render_backlog_markdown(result.excluded, min_confidence=min_confidence),
        encoding="utf-8",
    )

    print(f"可审计榜单已生成: {args.output_json}")
    print(f"榜单报告已生成: {args.output_md}")
    print(f"待核验清单已生成: {args.backlog_md}")
    print(f"包含 {len(result.included)} 人，待核验 {len(result.excluded)} 人。")


if __name__ == "__main__":
    main()
