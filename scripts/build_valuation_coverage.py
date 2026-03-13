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

from investor_method_lab.opportunity_trust_chain import load_validation_positions
from investor_method_lab.signal_ledger import load_ledger_entries, read_json
from investor_method_lab.valuation_coverage import (
    append_history,
    build_valuation_coverage,
    history_snapshot_record,
    load_focus_lookup,
    load_jsonl,
    load_real_rows,
    render_valuation_coverage_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build valuation coverage outputs for the hit-zone opportunity workflow")
    parser.add_argument(
        "--real-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunities.real_3markets.csv",
    )
    parser.add_argument(
        "--focus-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "dcf_special_focus_list.json",
    )
    parser.add_argument(
        "--ledger-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunity_signal_ledger.jsonl",
    )
    parser.add_argument(
        "--meta-file",
        type=Path,
        default=PROJECT_ROOT / "docs" / "opportunities_real_data_meta_3markets.json",
    )
    parser.add_argument(
        "--positions-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_validation_positions_latest.json",
    )
    parser.add_argument(
        "--confidence-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_confidence_latest.json",
    )
    parser.add_argument(
        "--review-writeback-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_review_writeback_latest.json",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "valuation_coverage_history.jsonl",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "valuation_coverage_latest.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "valuation_coverage_latest.md",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    real_rows = load_real_rows(args.real_file)
    if not real_rows:
        raise RuntimeError(f"real opportunities file is empty: {args.real_file}")
    signals = load_ledger_entries(args.ledger_file)
    if not signals:
        raise RuntimeError(f"signal ledger is empty: {args.ledger_file}")
    positions = load_validation_positions(args.positions_json)
    meta_payload = read_json(args.meta_file)
    focus_lookup = load_focus_lookup(args.focus_file)
    confidence_payload = read_json(args.confidence_json) if args.confidence_json.exists() else None
    review_writeback_payload = read_json(args.review_writeback_json) if args.review_writeback_json.exists() else None
    history_rows = load_jsonl(args.history_file)

    doc = build_valuation_coverage(
        real_rows=real_rows,
        signals=signals,
        positions=positions,
        focus_lookup=focus_lookup,
        meta_payload=meta_payload,
        confidence_payload=confidence_payload,
        review_writeback_payload=review_writeback_payload,
        history_rows=history_rows,
    )
    snapshot = history_snapshot_record(
        as_of_date=doc.get("as_of_date") or "",
        universe_summary=doc.get("overall_real_universe") or {},
        focus_summary=doc.get("focus_pool") or {},
        signal_summary=doc.get("signal_pool") or {},
    )
    append_history(args.history_file, snapshot)
    final_history_rows = load_jsonl(args.history_file)

    doc = build_valuation_coverage(
        real_rows=real_rows,
        signals=signals,
        positions=positions,
        focus_lookup=focus_lookup,
        meta_payload=meta_payload,
        confidence_payload=confidence_payload,
        review_writeback_payload=review_writeback_payload,
        history_rows=final_history_rows,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_valuation_coverage_markdown(doc), encoding="utf-8")

    print(
        json.dumps(
            {
                "real_rows": len(real_rows),
                "signals": len(signals),
                "positions": len(positions),
                "focus_pool": (doc.get("focus_pool") or {}).get("count", 0),
                "signal_pool": (doc.get("signal_pool") or {}).get("count", 0),
                "gap_rows": len(doc.get("gap_rows") or []),
                "history_rows": len(doc.get("trend") or []),
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
                "history_file": str(args.history_file),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
