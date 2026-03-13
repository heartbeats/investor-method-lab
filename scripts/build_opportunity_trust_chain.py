#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.opportunity_trust_chain import (
    DEFAULT_ANOMALY_STANDARD,
    DEFAULT_BENCHMARK_MAPPING,
    DEFAULT_FIELD_MAPPING,
    DEFAULT_REVIEW_STANDARD,
    DEFAULT_SNAPSHOT_ROOT,
    DEFAULT_SOURCE_WHITELIST,
    DEFAULT_TRUST_STANDARD,
    build_trust_outputs,
    load_contracts,
    load_validation_positions,
    render_confidence_markdown,
    render_review_queue_markdown,
)
from investor_method_lab.signal_ledger import load_ledger_entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build opportunity trust chain outputs from signal ledger + validation results")
    parser.add_argument("--ledger-file", type=Path, default=PROJECT_ROOT / "data" / "opportunity_signal_ledger.jsonl")
    parser.add_argument("--positions-json", type=Path, default=PROJECT_ROOT / "output" / "opportunity_validation_positions_latest.json")
    parser.add_argument("--trust-standard-file", type=Path, default=DEFAULT_TRUST_STANDARD)
    parser.add_argument("--review-standard-file", type=Path, default=DEFAULT_REVIEW_STANDARD)
    parser.add_argument("--field-mapping-file", type=Path, default=DEFAULT_FIELD_MAPPING)
    parser.add_argument("--source-whitelist-file", type=Path, default=DEFAULT_SOURCE_WHITELIST)
    parser.add_argument("--anomaly-standard-file", type=Path, default=DEFAULT_ANOMALY_STANDARD)
    parser.add_argument("--benchmark-mapping-file", type=Path, default=DEFAULT_BENCHMARK_MAPPING)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path(os.getenv("STOCK_DATA_SNAPSHOT_ROOT") or DEFAULT_SNAPSHOT_ROOT),
    )
    parser.add_argument("--snapshot-date", default=os.getenv("STOCK_DATA_SNAPSHOT_DATE", ""))
    parser.add_argument(
        "--output-field-lineage-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_field_lineage_latest.json",
    )
    parser.add_argument(
        "--output-confidence-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_confidence_latest.json",
    )
    parser.add_argument(
        "--output-review-queue-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_review_queue_latest.json",
    )
    parser.add_argument(
        "--output-confidence-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_confidence_latest.md",
    )
    parser.add_argument(
        "--output-review-queue-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_review_queue_latest.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    signals = load_ledger_entries(args.ledger_file)
    positions = load_validation_positions(args.positions_json)
    contracts = load_contracts(
        trust_standard_file=args.trust_standard_file,
        review_standard_file=args.review_standard_file,
        field_mapping_file=args.field_mapping_file,
        source_whitelist_file=args.source_whitelist_file,
        anomaly_standard_file=args.anomaly_standard_file,
        benchmark_mapping_file=args.benchmark_mapping_file,
    )
    outputs = build_trust_outputs(
        signals=signals,
        positions=positions,
        contracts=contracts,
        snapshot_root=args.snapshot_root,
        snapshot_date=args.snapshot_date,
    )
    args.output_field_lineage_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_field_lineage_json.write_text(json.dumps(outputs["lineage"], ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_confidence_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_confidence_json.write_text(json.dumps(outputs["confidence"], ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_review_queue_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_review_queue_json.write_text(json.dumps(outputs["review_queue"], ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_confidence_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_confidence_md.write_text(render_confidence_markdown(outputs["confidence"]), encoding="utf-8")
    args.output_review_queue_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_review_queue_md.write_text(render_review_queue_markdown(outputs["review_queue"]), encoding="utf-8")
    print(
        json.dumps(
            {
                "signals": len(signals),
                "positions": len(positions),
                "snapshot_root": str(args.snapshot_root),
                "output_field_lineage_json": str(args.output_field_lineage_json),
                "output_confidence_json": str(args.output_confidence_json),
                "output_review_queue_json": str(args.output_review_queue_json),
                "output_confidence_md": str(args.output_confidence_md),
                "output_review_queue_md": str(args.output_review_queue_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
