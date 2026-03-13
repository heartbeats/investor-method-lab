#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.opportunity_validation import (
    DEFAULT_SNAPSHOT_ROOT,
    build_history_loader,
    evaluate_signals,
    load_validation_rules,
    render_validation_markdown,
    summarize_validation,
)
from investor_method_lab.signal_ledger import load_ledger_entries, read_json

HOME_DIR = Path.home()
DEFAULT_RULES = HOME_DIR / "codex-project" / "data" / "unified_opportunity_validation_rules_v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build latest opportunity validation reports from the append-only signal ledger")
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
        "--rules-file",
        type=Path,
        default=DEFAULT_RULES,
    )
    parser.add_argument(
        "--validation-as-of",
        default="",
        help="Validation cutoff date YYYY-MM-DD. Defaults to latest meta as_of_date.",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path(os.getenv("STOCK_DATA_SNAPSHOT_ROOT") or DEFAULT_SNAPSHOT_ROOT),
        help="本地 snapshot 根目录，默认优先复用 stock-data-hub snapshots。",
    )
    parser.add_argument(
        "--snapshot-date",
        default=os.getenv("STOCK_DATA_SNAPSHOT_DATE", ""),
        help="指定 snapshot 日期 YYYY-MM-DD，默认取最新目录。",
    )
    parser.add_argument(
        "--hub-url",
        default=(os.getenv("IML_STOCK_DATA_HUB_URL") or "").strip(),
        help="可选 stock-data-hub 地址；未提供时仅用 snapshot + yfinance。",
    )
    parser.add_argument(
        "--disable-yfinance-fallback",
        action="store_true",
        help="禁用 yfinance 兜底，仅使用 snapshot/hub。",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_validation_latest.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_validation_latest.md",
    )
    parser.add_argument(
        "--output-positions-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_validation_positions_latest.json",
    )
    return parser.parse_args()



def infer_validation_as_of_date(meta_file: Path, fallback: str = "") -> str:
    if meta_file.exists():
        payload = read_json(meta_file)
        dates = payload.get("as_of_dates") or []
        if dates:
            return str(dates[-1])
    return fallback



def main() -> None:
    args = parse_args()
    signals = load_ledger_entries(args.ledger_file)
    if not signals:
        raise RuntimeError(f"signal ledger is empty: {args.ledger_file}")
    validation_as_of = args.validation_as_of or infer_validation_as_of_date(args.meta_file)
    if not validation_as_of:
        raise RuntimeError("validation_as_of date is required")
    validation_date = datetime.strptime(validation_as_of, "%Y-%m-%d").date()
    rules = load_validation_rules(args.rules_file)
    history_loader = build_history_loader(
        snapshot_root=args.snapshot_root,
        snapshot_date=args.snapshot_date,
        hub_url=args.hub_url,
        allow_yfinance_fallback=not args.disable_yfinance_fallback,
    )

    positions = evaluate_signals(
        signals=signals,
        validation_rules=rules,
        validation_as_of_date=validation_date,
        history_loader=history_loader,
    )
    summary = summarize_validation(
        positions=positions,
        validation_rules=rules,
        validation_as_of_date=validation_date,
        ledger_file=args.ledger_file,
    )
    summary["positions_file"] = str(args.output_positions_json)
    summary["history_loader_context"] = history_loader.describe()

    args.output_positions_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_positions_json.write_text(json.dumps({"positions": positions}, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_validation_markdown(summary, positions), encoding="utf-8")

    print(json.dumps({
        "ledger_file": str(args.ledger_file),
        "validation_as_of": validation_as_of,
        "signals": len(signals),
        "positions": len(positions),
        "snapshot_dir": summary["history_loader_context"].get("snapshot_dir"),
        "hub_url": summary["history_loader_context"].get("hub_url"),
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
        "output_positions_json": str(args.output_positions_json),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
