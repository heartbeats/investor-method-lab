#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.signal_ledger import read_json
from investor_method_lab.valuation_upgrade_backlog import (
    build_source_upgrade_backlog,
    load_real_rows,
    load_signals,
    render_source_upgrade_backlog_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build valuation source upgrade backlog from latest valuation coverage report")
    parser.add_argument(
        "--coverage-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "valuation_coverage_latest.json",
    )
    parser.add_argument(
        "--real-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real_3markets.csv",
    )
    parser.add_argument(
        "--ledger-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunity_signal_ledger.jsonl",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "data" / "source_upgrade_backlog.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "valuation_upgrade_backlog_latest.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    coverage_doc = read_json(args.coverage_json)
    real_rows = load_real_rows(args.real_file)
    signals = load_signals(args.ledger_file)
    doc = build_source_upgrade_backlog(
        coverage_doc=coverage_doc,
        real_rows=real_rows,
        signals=signals,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_source_upgrade_backlog_markdown(doc), encoding="utf-8")

    print(json.dumps({
        "items": len(doc.get("items") or []),
        "lanes": len(doc.get("lanes") or []),
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
