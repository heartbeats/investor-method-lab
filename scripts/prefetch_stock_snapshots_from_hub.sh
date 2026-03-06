#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:-/Users/$(id -un 2>/dev/null || echo lucas)}"
HUB_SCRIPT="${HOME_DIR}/projects/stock-data-hub/scripts/build_local_stock_snapshot.py"
SYMBOLS_FILE="${1:-$ROOT_DIR/data/opportunities.universe_core_3markets.csv}"
OUTPUT_ROOT="${STOCK_DATA_SNAPSHOT_ROOT:-${HOME_DIR}/projects/stock-data-hub/data_lake/snapshots}"
PREFETCH_DOMAINS="${IML_SNAPSHOT_PREFETCH_DOMAINS:-quotes,fundamentals,external_valuations,price_history,financial_statements}"
if [[ $# -gt 0 ]]; then
  shift
fi

if [[ ! -f "$HUB_SCRIPT" ]]; then
  echo "stock-data-hub snapshot script not found: $HUB_SCRIPT" >&2
  exit 1
fi

python3 "$HUB_SCRIPT" \
  --symbols-file "$SYMBOLS_FILE" \
  --output-root "$OUTPUT_ROOT" \
  --mode non_realtime \
  --domains "$PREFETCH_DOMAINS" \
  "$@"
