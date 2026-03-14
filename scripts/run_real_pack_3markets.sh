#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:-/Users/$(id -un 2>/dev/null || echo lucas)}"

UNIVERSE_FILE="${1:-$ROOT_DIR/data/opportunities.universe_core_3markets.csv}"
REAL_FILE="$ROOT_DIR/data/opportunities.real_3markets.csv"
META_FILE="$ROOT_DIR/docs/opportunities_real_data_meta_3markets.json"
REPORT_FILE="$ROOT_DIR/docs/top20_opportunity_pack_real_3markets.md"
TOP_FILE="$ROOT_DIR/output/top20_first_batch_opportunities_real_3markets.csv"
GROUP_FILE="$ROOT_DIR/output/top20_methodology_top5_by_group_real_3markets.csv"
DIVERSIFIED_FILE="$ROOT_DIR/output/top20_diversified_opportunities_real_3markets.csv"
TIERED_GROUP_FILE="$ROOT_DIR/output/top20_methodology_top10_by_group_tiered_real_3markets.csv"
TRACE_FILE="$ROOT_DIR/output/method_decision_trace_real_3markets.json"
PLAYBOOK_FILE="$ROOT_DIR/docs/methodology_playbook_v4.md"
RULEBOOK_FILE="$ROOT_DIR/data/methodology_rulebook_v4.json"
DCF_BASE_URL="${DCF_BASE_URL:-http://127.0.0.1:8000}"
IML_STOCK_DATA_HUB_URL="${IML_STOCK_DATA_HUB_URL:-http://127.0.0.1:18123}"
SNAPSHOT_ROOT="${STOCK_DATA_SNAPSHOT_ROOT:-${HOME_DIR}/projects/stock-data-hub/data_lake/snapshots}"
SNAPSHOT_DATE="${STOCK_DATA_SNAPSHOT_DATE:-}"
PREFETCH_SCRIPT="$ROOT_DIR/scripts/prefetch_stock_snapshots_from_hub.sh"
WATCHLIST_SYNC_SCRIPT="$ROOT_DIR/scripts/sync_watchlist_to_hub.py"
FOCUS_FILE="$ROOT_DIR/data/dcf_special_focus_list.json"
FOCUS_REPORT_FILE="$ROOT_DIR/docs/dcf_special_focus_daily.md"
OPPORTUNITY_REPORT_FILE="$ROOT_DIR/docs/opportunity_mining_daily.md"
DUAL_MODULES_JSON="$ROOT_DIR/docs/daily_dual_modules.json"
LEDGER_FILE="$ROOT_DIR/data/opportunity_signal_ledger.jsonl"
LEDGER_LATEST_MD="$ROOT_DIR/output/opportunity_signal_ledger_latest.md"
LEDGER_LATEST_JSON="$ROOT_DIR/output/opportunity_signal_ledger_latest.json"
VALIDATION_LATEST_JSON="$ROOT_DIR/output/opportunity_validation_latest.json"
VALIDATION_LATEST_MD="$ROOT_DIR/output/opportunity_validation_latest.md"
VALIDATION_POSITIONS_JSON="$ROOT_DIR/output/opportunity_validation_positions_latest.json"
FIELD_LINEAGE_JSON="$ROOT_DIR/output/opportunity_field_lineage_latest.json"
CONFIDENCE_JSON="$ROOT_DIR/output/opportunity_confidence_latest.json"
CONFIDENCE_MD="$ROOT_DIR/output/opportunity_confidence_latest.md"
REVIEW_QUEUE_JSON="$ROOT_DIR/output/opportunity_review_queue_latest.json"
REVIEW_QUEUE_MD="$ROOT_DIR/output/opportunity_review_queue_latest.md"
REVIEW_WRITEBACK_JSON="$ROOT_DIR/output/opportunity_review_writeback_latest.json"
REVIEW_WRITEBACK_MD="$ROOT_DIR/output/opportunity_review_writeback_latest.md"
REVIEW_BACKLOG_JSON="$ROOT_DIR/output/opportunity_review_backlog_latest.json"
REVIEW_BACKLOG_MD="$ROOT_DIR/output/opportunity_review_backlog_latest.md"
VALUATION_COVERAGE_JSON="$ROOT_DIR/output/valuation_coverage_latest.json"
VALUATION_COVERAGE_MD="$ROOT_DIR/output/valuation_coverage_latest.md"
VALUATION_COVERAGE_HISTORY="$ROOT_DIR/data/valuation_coverage_history.jsonl"
SOURCE_UPGRADE_BACKLOG_JSON="$ROOT_DIR/data/source_upgrade_backlog.json"
VALUATION_UPGRADE_BACKLOG_MD="$ROOT_DIR/output/valuation_upgrade_backlog_latest.md"
PER_TICKER_TIMEOUT_SECONDS="${IML_PER_TICKER_TIMEOUT_SECONDS:-8}"
PER_TICKER_RETRIES="${IML_PER_TICKER_RETRIES:-2}"
PER_TICKER_RETRY_TIMEOUT_MULTIPLIER="${IML_PER_TICKER_RETRY_TIMEOUT_MULTIPLIER:-1.6}"
PER_TICKER_RETRY_BACKOFF_SECONDS="${IML_PER_TICKER_RETRY_BACKOFF_SECONDS:-0.25}"
CODEX_PROJECT_ROOT="${CODEX_PROJECT_ROOT:-${HOME_DIR}/codex-project}"
REVIEW_QUEUE_SYNC_SCRIPT="${CODEX_PROJECT_ROOT}/scripts/sync_hit_zone_review_queue_bitable.py"
REVIEW_WRITEBACK_PULL_SCRIPT="${CODEX_PROJECT_ROOT}/scripts/pull_hit_zone_review_queue_writeback.py"
MARKET_DATA_HARVEST_SCRIPT="${CODEX_PROJECT_ROOT}/scripts/harvest_market_data_lake.py"
CORE_DATA_COVERAGE_SCRIPT="${CODEX_PROJECT_ROOT}/scripts/build_core_data_coverage_report.py"
MARKET_DATA_INCREMENTAL_DB="${MARKET_DATA_INCREMENTAL_DB:-${HOME_DIR}/projects/stock-data-hub/data_lake/incremental/market_data_incremental.db}"

export IML_STOCK_DATA_HUB_URL

if [[ $# -eq 0 ]]; then
  python3 "$ROOT_DIR/scripts/build_universe_core_3markets.py" \
    --output-file "$UNIVERSE_FILE" \
    --seed-file "$ROOT_DIR/data/opportunities.universe_3markets.csv"
fi

if [[ "${IML_SYNC_WATCHLIST_TO_HUB:-1}" == "1" ]] && [[ -f "$WATCHLIST_SYNC_SCRIPT" ]]; then
  python3 "$WATCHLIST_SYNC_SCRIPT" \
    --source investor-method-lab \
    --symbols-file "$UNIVERSE_FILE" \
    --hub-url "$IML_STOCK_DATA_HUB_URL" \
    --replace || echo "[warn] watchlist sync failed, continue"
fi

if [[ "${IML_PREFETCH_SNAPSHOT_FROM_HUB:-1}" == "1" ]] && [[ -x "$PREFETCH_SCRIPT" ]]; then
  if [[ -n "$SNAPSHOT_DATE" ]]; then
    "$PREFETCH_SCRIPT" "$UNIVERSE_FILE" --date "$SNAPSHOT_DATE" || echo "[warn] snapshot prefetch failed, continue online fetch"
  else
    "$PREFETCH_SCRIPT" "$UNIVERSE_FILE" || echo "[warn] snapshot prefetch failed, continue online fetch"
  fi
fi

SNAPSHOT_DATE_ARGS=()
if [[ -n "$SNAPSHOT_DATE" ]]; then
  SNAPSHOT_DATE_ARGS+=(--snapshot-date "$SNAPSHOT_DATE")
fi

BUILD_REAL_ARGS=(
  --universe-file "$UNIVERSE_FILE"
  --output-file "$REAL_FILE"
  --meta-file "$META_FILE"
  --allow-partial
  --per-ticker-timeout-seconds "$PER_TICKER_TIMEOUT_SECONDS"
  --per-ticker-retries "$PER_TICKER_RETRIES"
  --per-ticker-retry-timeout-multiplier "$PER_TICKER_RETRY_TIMEOUT_MULTIPLIER"
  --per-ticker-retry-backoff-seconds "$PER_TICKER_RETRY_BACKOFF_SECONDS"
  --dcf-base-url "$DCF_BASE_URL"
  --snapshot-root "$SNAPSHOT_ROOT"
)
if [[ -n "$SNAPSHOT_DATE" ]]; then
  BUILD_REAL_ARGS+=(--snapshot-date "$SNAPSHOT_DATE")
fi

python3 "$ROOT_DIR/scripts/build_real_opportunities.py" "${BUILD_REAL_ARGS[@]}"

AS_OF_DATE="$(ROOT_DIR="$ROOT_DIR" python3 - << 'PY'
import csv
import json
import os
import re
from pathlib import Path
root = Path(os.environ["ROOT_DIR"])
dates = set()
meta_file = root / "docs" / "opportunities_real_data_meta_3markets.json"
if meta_file.exists():
    doc = json.loads(meta_file.read_text(encoding="utf-8"))
    for value in doc.get("as_of_dates") or []:
        text = str(value).strip()
        if text:
            dates.add(text)
real_file = root / "data" / "opportunities.real_3markets.csv"
pattern = re.compile(r"real-data@(\d{4}-\d{2}-\d{2})")
if real_file.exists():
    with real_file.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            note = str(row.get("note") or "")
            match = pattern.search(note)
            if match:
                dates.add(match.group(1))
print(max(dates) if dates else "")
PY
)"

python3 "$ROOT_DIR/scripts/generate_top20_opportunity_pack.py" \
  --opportunities-file "$REAL_FILE" \
  --engine-version v4 \
  --rulebook-file "$RULEBOOK_FILE" \
  --output-csv "$TOP_FILE" \
  --output-group-csv "$GROUP_FILE" \
  --output-diversified-csv "$DIVERSIFIED_FILE" \
  --output-tiered-group-csv "$TIERED_GROUP_FILE" \
  --output-decision-trace-json "$TRACE_FILE" \
  --output-playbook-md "$PLAYBOOK_FILE" \
  --output-md "$REPORT_FILE" \
  --as-of-date "$AS_OF_DATE" \
  --top 10 \
  --per-group-top 5 \
  --per-tier-top 10 \
  --max-per-sector 2

python3 "$ROOT_DIR/scripts/build_dual_daily_modules.py" \
  --focus-file "$FOCUS_FILE" \
  --top-file "$TOP_FILE" \
  --real-file "$REAL_FILE" \
  --meta-file "$META_FILE" \
  --as-of-date "$AS_OF_DATE" \
  --output-focus-md "$FOCUS_REPORT_FILE" \
  --output-opportunity-md "$OPPORTUNITY_REPORT_FILE" \
  --output-json "$DUAL_MODULES_JSON" \
  --opportunity-top 10

python3 "$ROOT_DIR/scripts/update_opportunity_signal_ledger.py" \
  --focus-file "$FOCUS_FILE" \
  --top-file "$TOP_FILE" \
  --real-file "$REAL_FILE" \
  --trace-file "$TRACE_FILE" \
  --meta-file "$META_FILE" \
  --ledger-file "$LEDGER_FILE" \
  --output-md "$LEDGER_LATEST_MD" \
  --output-json "$LEDGER_LATEST_JSON"

python3 "$ROOT_DIR/scripts/build_opportunity_validation.py" \
  --ledger-file "$LEDGER_FILE" \
  --meta-file "$META_FILE" \
  --validation-as-of "$AS_OF_DATE" \
  --output-json "$VALIDATION_LATEST_JSON" \
  --output-md "$VALIDATION_LATEST_MD" \
  --output-positions-json "$VALIDATION_POSITIONS_JSON"

python3 "$ROOT_DIR/scripts/build_opportunity_trust_chain.py" \
  --ledger-file "$LEDGER_FILE" \
  --positions-json "$VALIDATION_POSITIONS_JSON" \
  --snapshot-root "$SNAPSHOT_ROOT" \
  --snapshot-date "$SNAPSHOT_DATE" \
  --output-field-lineage-json "$FIELD_LINEAGE_JSON" \
  --output-confidence-json "$CONFIDENCE_JSON" \
  --output-review-queue-json "$REVIEW_QUEUE_JSON" \
  --output-confidence-md "$CONFIDENCE_MD" \
  --output-review-queue-md "$REVIEW_QUEUE_MD"

if [[ "${IML_PULL_REVIEW_WRITEBACK_FROM_FEISHU:-0}" == "1" ]] && [[ -f "$REVIEW_WRITEBACK_PULL_SCRIPT" ]]; then
  REVIEW_WRITEBACK_PULL_ARGS=(--project-root "$ROOT_DIR")
  if [[ "${IML_PULL_REVIEW_WRITEBACK_DRY_RUN:-0}" == "1" ]]; then
    REVIEW_WRITEBACK_PULL_ARGS+=(--dry-run)
  fi
  if [[ "${IML_MARK_REVIEW_WRITEBACK_STATUS:-1}" == "0" ]]; then
    REVIEW_WRITEBACK_PULL_ARGS+=(--no-mark-written-back)
  fi
  python3 "$REVIEW_WRITEBACK_PULL_SCRIPT" "${REVIEW_WRITEBACK_PULL_ARGS[@]}" || echo "[warn] review queue writeback pull failed, continue"
fi

python3 "$ROOT_DIR/scripts/generate_top20_opportunity_pack.py" \
  --opportunities-file "$REAL_FILE" \
  --engine-version v4 \
  --rulebook-file "$RULEBOOK_FILE" \
  --output-csv "$TOP_FILE" \
  --output-group-csv "$GROUP_FILE" \
  --output-diversified-csv "$DIVERSIFIED_FILE" \
  --output-tiered-group-csv "$TIERED_GROUP_FILE" \
  --output-decision-trace-json "$TRACE_FILE" \
  --output-playbook-md "$PLAYBOOK_FILE" \
  --output-md "$REPORT_FILE" \
  --as-of-date "$AS_OF_DATE" \
  --top 10 \
  --per-group-top 5 \
  --per-tier-top 10 \
  --max-per-sector 2 \
  --validation-positions-json "$VALIDATION_POSITIONS_JSON" \
  --confidence-json "$CONFIDENCE_JSON" \
  --field-lineage-json "$FIELD_LINEAGE_JSON" \
  --review-writeback-json "$REVIEW_WRITEBACK_JSON"

python3 "$ROOT_DIR/scripts/build_valuation_coverage.py" \
  --real-file "$REAL_FILE" \
  --focus-file "$FOCUS_FILE" \
  --ledger-file "$LEDGER_FILE" \
  --meta-file "$META_FILE" \
  --positions-json "$VALIDATION_POSITIONS_JSON" \
  --confidence-json "$CONFIDENCE_JSON" \
  --review-writeback-json "$REVIEW_WRITEBACK_JSON" \
  --history-file "$VALUATION_COVERAGE_HISTORY" \
  --output-json "$VALUATION_COVERAGE_JSON" \
  --output-md "$VALUATION_COVERAGE_MD"

python3 "$ROOT_DIR/scripts/build_valuation_upgrade_backlog.py" \
  --coverage-json "$VALUATION_COVERAGE_JSON" \
  --real-file "$REAL_FILE" \
  --ledger-file "$LEDGER_FILE" \
  --output-json "$SOURCE_UPGRADE_BACKLOG_JSON" \
  --output-md "$VALUATION_UPGRADE_BACKLOG_MD"

if [[ -f "$MARKET_DATA_HARVEST_SCRIPT" ]]; then
  HARVEST_ARGS=(
    --symbols-file "$UNIVERSE_FILE"
    --snapshot-root "$SNAPSHOT_ROOT"
    --db-path "$MARKET_DATA_INCREMENTAL_DB"
    --build-snapshot-if-missing
  )
  if [[ -n "$SNAPSHOT_DATE" ]]; then
    HARVEST_ARGS+=(--snapshot-date "$SNAPSHOT_DATE")
  fi
  python3 "$MARKET_DATA_HARVEST_SCRIPT" "${HARVEST_ARGS[@]}" || echo "[warn] market data harvest failed, continue"
fi

if [[ -f "$CORE_DATA_COVERAGE_SCRIPT" ]]; then
  python3 "$CORE_DATA_COVERAGE_SCRIPT" \
    --iml-root "$ROOT_DIR" \
    --db-path "$MARKET_DATA_INCREMENTAL_DB" || echo "[warn] core data coverage build failed, continue"
fi

if [[ "${IML_SYNC_REVIEW_QUEUE_TO_FEISHU:-0}" == "1" ]] && [[ -f "$REVIEW_QUEUE_SYNC_SCRIPT" ]]; then
  REVIEW_QUEUE_SYNC_ARGS=(--input-file "$REVIEW_QUEUE_JSON")
  if [[ "${IML_SYNC_REVIEW_QUEUE_DRY_RUN:-0}" == "1" ]]; then
    REVIEW_QUEUE_SYNC_ARGS+=(--dry-run)
  fi
  if [[ "${IML_SYNC_REVIEW_QUEUE_ENSURE_EDITABLE:-0}" == "1" ]]; then
    REVIEW_QUEUE_SYNC_ARGS+=(--ensure-editable)
  fi
  python3 "$REVIEW_QUEUE_SYNC_SCRIPT" "${REVIEW_QUEUE_SYNC_ARGS[@]}" || echo "[warn] review queue Feishu sync failed, continue"
fi

echo "三市场实时机会包已生成:"
echo "- $REPORT_FILE"
echo "- $TOP_FILE"
echo "- $GROUP_FILE"
echo "- $DIVERSIFIED_FILE"
echo "- $TIERED_GROUP_FILE"
echo "- $TRACE_FILE"
echo "- $PLAYBOOK_FILE"
echo "- $REAL_FILE"
echo "- $META_FILE"
echo "- $FOCUS_REPORT_FILE"
echo "- $OPPORTUNITY_REPORT_FILE"
echo "- $DUAL_MODULES_JSON"
echo "- $LEDGER_FILE"
echo "- $LEDGER_LATEST_MD"
echo "- $LEDGER_LATEST_JSON"
echo "- $VALIDATION_LATEST_JSON"
echo "- $VALIDATION_LATEST_MD"
echo "- $VALIDATION_POSITIONS_JSON"
echo "- $FIELD_LINEAGE_JSON"
echo "- $CONFIDENCE_JSON"
echo "- $CONFIDENCE_MD"
echo "- $REVIEW_QUEUE_JSON"
echo "- $REVIEW_QUEUE_MD"
echo "- $REVIEW_WRITEBACK_JSON"
echo "- $REVIEW_WRITEBACK_MD"
echo "- $REVIEW_BACKLOG_JSON"
echo "- $REVIEW_BACKLOG_MD"
echo "- $VALUATION_COVERAGE_JSON"
echo "- $VALUATION_COVERAGE_MD"
echo "- $SOURCE_UPGRADE_BACKLOG_JSON"
echo "- $VALUATION_UPGRADE_BACKLOG_MD"
