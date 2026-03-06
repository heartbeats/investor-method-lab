#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib import request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步项目股票池到 stock-data-hub watchlist")
    parser.add_argument("--source", default="investor-method-lab", help="watchlist source name")
    parser.add_argument(
        "--symbols-file",
        type=Path,
        required=True,
        help="CSV file with ticker/symbol column",
    )
    parser.add_argument("--hub-url", required=True, help="stock-data-hub base URL")
    parser.add_argument("--replace", action="store_true", help="replace source symbols")
    return parser.parse_args()


def load_symbols(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    symbols: list[str] = []
    for row in rows:
        raw = str(row.get("symbol") or row.get("ticker") or "").strip()
        if raw:
            symbols.append(raw)
    return sorted(set(symbols))


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=20.0) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("unexpected response payload")
    return parsed


def main() -> None:
    args = parse_args()
    symbols = load_symbols(args.symbols_file)
    payload = {
        "source": args.source,
        "symbols": symbols,
        "replace": bool(args.replace),
    }
    url = args.hub_url.rstrip("/") + "/v1/watchlist/upsert"
    result = post_json(url, payload)
    print(
        f"watchlist synced: source={args.source} input={len(symbols)} "
        f"merged={int(result.get('symbol_count', 0))}"
    )


if __name__ == "__main__":
    main()

