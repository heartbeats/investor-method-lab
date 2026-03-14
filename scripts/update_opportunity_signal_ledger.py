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

from investor_method_lab.signal_ledger import (
    append_signal_entries,
    build_latest_summary,
    build_refresh_reissue_entries,
    build_signal_entries,
    load_benchmark_config,
    load_existing_signal_ids,
    load_focus_tickers,
    load_ledger_entries,
    read_csv_rows,
    read_json,
    render_latest_markdown,
)

HOME_DIR = Path.home()


def resolve_hit_zone_data_dir() -> Path:
    candidates = [
        os.getenv("HIT_ZONE_PROJECT_DIR"),
        str(HOME_DIR / "projects" / "hit-zone"),
        str(HOME_DIR / "projects" / "dcf-suite"),
        str(HOME_DIR / "codex-project"),
    ]
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        root = Path(text).expanduser()
        data_dir = root / "data"
        if data_dir.exists():
            return data_dir
    return HOME_DIR / "projects" / "hit-zone" / "data"


HIT_ZONE_DATA_DIR = resolve_hit_zone_data_dir()
DEFAULT_BENCHMARK_CONFIG = HIT_ZONE_DATA_DIR / "unified_benchmark_mapping_v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append daily opportunity signals into the append-only ledger")
    parser.add_argument("--top-file", type=Path, required=True)
    parser.add_argument("--real-file", type=Path, required=True)
    parser.add_argument("--trace-file", type=Path, required=True)
    parser.add_argument("--meta-file", type=Path, required=True)
    parser.add_argument("--focus-file", type=Path, default=None)
    parser.add_argument(
        "--ledger-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "opportunity_signal_ledger.jsonl",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_signal_ledger_latest.md",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "output" / "opportunity_signal_ledger_latest.json",
    )
    parser.add_argument(
        "--benchmark-config",
        type=Path,
        default=DEFAULT_BENCHMARK_CONFIG,
    )
    parser.add_argument(
        "--source-list-id",
        default="opportunity_mining_daily",
        help="Stable source list id for signal dedupe and downstream validation",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    top_rows = read_csv_rows(args.top_file)
    real_rows = read_csv_rows(args.real_file)
    trace_payload = read_json(args.trace_file)
    meta_payload = read_json(args.meta_file)
    focus_tickers = load_focus_tickers(args.focus_file)
    benchmark_config = load_benchmark_config(args.benchmark_config)

    artifact_paths = {
        "top_file": args.top_file,
        "real_file": args.real_file,
        "trace_file": args.trace_file,
        "meta_file": args.meta_file,
    }
    if args.focus_file:
        artifact_paths["focus_file"] = args.focus_file

    candidate_entries = build_signal_entries(
        top_rows=top_rows,
        real_rows=real_rows,
        trace_payload=trace_payload,
        meta_payload=meta_payload,
        benchmark_config=benchmark_config,
        artifact_paths=artifact_paths,
        source_list_id=args.source_list_id,
        focus_tickers=focus_tickers,
    )

    existing_ledger_entries = load_ledger_entries(args.ledger_file)
    existing_ids = load_existing_signal_ids(args.ledger_file)
    effective_candidate_entries = [
        entry for entry in candidate_entries if entry.get("signal_id") not in existing_ids
    ]
    refresh_entries = build_refresh_reissue_entries(
        ledger_entries=existing_ledger_entries,
        current_batch_entries=effective_candidate_entries,
        real_rows=real_rows,
        meta_payload=meta_payload,
        artifact_paths=artifact_paths,
        refresh_source_list_id=f"{args.source_list_id}_refresh_reissue",
        focus_tickers=focus_tickers,
    )
    batch_entries = candidate_entries + refresh_entries

    new_entries = [entry for entry in batch_entries if entry.get("signal_id") not in existing_ids]
    if new_entries:
        append_signal_entries(args.ledger_file, new_entries)

    ledger_entries = load_ledger_entries(args.ledger_file)
    summary = build_latest_summary(
        ledger_path=args.ledger_file,
        ledger_entries=ledger_entries,
        batch_entries=batch_entries,
        newly_appended_entries=new_entries,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_latest_markdown(summary), encoding="utf-8")

    print(json.dumps({
        "ledger_file": str(args.ledger_file),
        "candidate_entries": len(candidate_entries),
        "refresh_entries": len(refresh_entries),
        "new_entries": len(new_entries),
        "latest_as_of_date": summary.get("latest_as_of_date"),
        "latest_signal_count": summary.get("latest_signal_count"),
        "output_json": str(args.output_json),
        "output_md": str(args.output_md),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
