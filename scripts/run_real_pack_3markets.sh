#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

UNIVERSE_FILE="${1:-$ROOT_DIR/data/opportunities.universe_3markets.csv}"
REAL_FILE="$ROOT_DIR/data/opportunities.real_3markets.csv"
META_FILE="$ROOT_DIR/docs/opportunities_real_data_meta_3markets.json"
REPORT_FILE="$ROOT_DIR/docs/top20_opportunity_pack_real_3markets.md"
TOP_FILE="$ROOT_DIR/output/top20_first_batch_opportunities_real_3markets.csv"
GROUP_FILE="$ROOT_DIR/output/top20_methodology_top5_by_group_real_3markets.csv"
DIVERSIFIED_FILE="$ROOT_DIR/output/top20_diversified_opportunities_real_3markets.csv"

python3 "$ROOT_DIR/scripts/build_real_opportunities.py" \
  --universe-file "$UNIVERSE_FILE" \
  --output-file "$REAL_FILE" \
  --meta-file "$META_FILE"

AS_OF_DATE="$(ROOT_DIR="$ROOT_DIR" python3 - << 'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["ROOT_DIR"])
p = root / "docs" / "opportunities_real_data_meta_3markets.json"
doc = json.loads(p.read_text(encoding="utf-8"))
dates = doc.get("as_of_dates") or []
print(dates[-1] if dates else "")
PY
)"

python3 "$ROOT_DIR/scripts/generate_top20_opportunity_pack.py" \
  --opportunities-file "$REAL_FILE" \
  --output-csv "$TOP_FILE" \
  --output-group-csv "$GROUP_FILE" \
  --output-diversified-csv "$DIVERSIFIED_FILE" \
  --output-md "$REPORT_FILE" \
  --as-of-date "$AS_OF_DATE" \
  --top 10 \
  --per-group-top 5 \
  --max-per-sector 2

echo "三市场实时机会包已生成:"
echo "- $REPORT_FILE"
echo "- $TOP_FILE"
echo "- $GROUP_FILE"
echo "- $DIVERSIFIED_FILE"
echo "- $REAL_FILE"
echo "- $META_FILE"
