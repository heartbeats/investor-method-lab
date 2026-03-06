#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:-/Users/$(id -un 2>/dev/null || echo lucas)}"

HUB_ROOT="${IML_STOCK_DATA_HUB_ROOT:-${HOME_DIR}/projects/stock-data-hub}"
HUB_HOST="${IML_STOCK_DATA_HUB_HOST:-127.0.0.1}"
HUB_PORT="${IML_STOCK_DATA_HUB_PORT:-18123}"
HUB_URL="${IML_STOCK_DATA_HUB_URL:-http://${HUB_HOST}:${HUB_PORT}}"
HUB_LOG="${IML_STOCK_DATA_HUB_LOG:-/tmp/iml_stock_data_hub.log}"
HUB_WORKERS="${IML_STOCK_DATA_HUB_WORKERS:-2}"

export IML_STOCK_DATA_HUB_URL="${HUB_URL}"
export STOCK_DATA_QUOTE_CHAIN_A="${STOCK_DATA_QUOTE_CHAIN_A:-akshare,yfinance}"
export STOCK_DATA_QUOTE_CHAIN_HK="${STOCK_DATA_QUOTE_CHAIN_HK:-yfinance}"
export STOCK_DATA_QUOTE_CHAIN_US="${STOCK_DATA_QUOTE_CHAIN_US:-yfinance,fmp,alpha_vantage}"
export STOCK_DATA_BATCH_MAX_WORKERS="${STOCK_DATA_BATCH_MAX_WORKERS:-6}"

HUB_PID=""
HUB_STARTED_BY_SCRIPT=0

check_hub_health() {
  python3 - "$HUB_URL" <<'PY'
import json
import sys
from urllib import request
url = sys.argv[1].rstrip("/") + "/health"
try:
    opener = request.build_opener(request.ProxyHandler({}))
    with opener.open(url, timeout=2.5) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    ok = bool(payload.get("ok"))
except Exception:
    ok = False
print("ok" if ok else "down")
raise SystemExit(0 if ok else 1)
PY
}

cleanup() {
  if [[ "$HUB_STARTED_BY_SCRIPT" == "1" && -n "$HUB_PID" ]]; then
    kill "$HUB_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if ! check_hub_health >/dev/null 2>&1; then
  if [[ ! -d "$HUB_ROOT/src/stock_data_hub" ]]; then
    echo "stock-data-hub not found: $HUB_ROOT" >&2
    exit 2
  fi
  echo "[with-hub] start stock-data-hub: ${HUB_URL}"
  PYTHONPATH="${HUB_ROOT}/src" python3 -m uvicorn stock_data_hub.main:app \
    --host "$HUB_HOST" --port "$HUB_PORT" --workers "$HUB_WORKERS" >"$HUB_LOG" 2>&1 &
  HUB_PID="$!"
  HUB_STARTED_BY_SCRIPT=1
  for _ in $(seq 1 20); do
    if check_hub_health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! check_hub_health >/dev/null 2>&1; then
    echo "stock-data-hub failed to start; log: $HUB_LOG" >&2
    exit 3
  fi
fi

echo "[with-hub] running real pack with hub: ${IML_STOCK_DATA_HUB_URL}"
bash "$ROOT_DIR/scripts/run_real_pack_3markets.sh" "$@"
