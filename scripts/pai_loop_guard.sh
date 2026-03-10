#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/output/pai_loop"
ALERT_LOG="$LOG_DIR/alert.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_FILE="${PAI_ENV_FILE:-$ROOT_DIR/.env.pai}"
NOTIFY_ENV_FILE="${PAI_NOTIFY_ENV_FILE:-$HOME/.config/dcf_notify.env}"
FEISHU_SEND_SCRIPT="${PAI_FEISHU_SEND_SCRIPT:-$HOME/codex-project/scripts/send_feishu_text_message.py}"
PAI_NOTIFY_ON_SUCCESS_OVERRIDE="${PAI_NOTIFY_ON_SUCCESS-__UNSET__}"
HOME_DIR="${HOME:-/Users/$(id -un 2>/dev/null || echo lucas)}"
HUB_ROOT="${IML_STOCK_DATA_HUB_ROOT:-${HOME_DIR}/projects/stock-data-hub}"
HUB_HOST="${IML_STOCK_DATA_HUB_HOST:-127.0.0.1}"
HUB_PORT="${IML_STOCK_DATA_HUB_PORT:-18123}"
HUB_URL="${IML_STOCK_DATA_HUB_URL:-http://${HUB_HOST}:${HUB_PORT}}"
HUB_LOG="${IML_STOCK_DATA_HUB_LOG:-/tmp/iml_stock_data_hub.log}"
HUB_WORKERS="${IML_STOCK_DATA_HUB_WORKERS:-2}"
HUB_PYTHON="${IML_STOCK_DATA_HUB_PYTHON:-${HUB_ROOT}/.venv/bin/python}"
HUB_PID=""
HUB_STARTED_BY_GUARD=0

mkdir -p "$LOG_DIR"

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

resolve_hub_python() {
  if [ -x "$HUB_PYTHON" ]; then
    printf '%s\n' "$HUB_PYTHON"
    return 0
  fi
  command -v python3
}

ensure_hub_ready() {
  export IML_STOCK_DATA_HUB_URL="$HUB_URL"
  if check_hub_health >/dev/null 2>&1; then
    return 0
  fi
  if [ ! -d "$HUB_ROOT/src/stock_data_hub" ]; then
    echo "[pai-loop-guard] stock-data-hub not found: $HUB_ROOT" >&2
    return 2
  fi

  local hub_python
  hub_python="$(resolve_hub_python)"
  echo "[pai-loop-guard] start stock-data-hub: ${HUB_URL}"
  PYTHONPATH="$HUB_ROOT/src:${PYTHONPATH:-}" "$hub_python" -m uvicorn stock_data_hub.main:app     --host "$HUB_HOST" --port "$HUB_PORT" --workers "$HUB_WORKERS" >"$HUB_LOG" 2>&1 &
  HUB_PID="$!"
  HUB_STARTED_BY_GUARD=1
  disown "$HUB_PID" >/dev/null 2>&1 || true

  for _ in $(seq 1 20); do
    if check_hub_health >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "[pai-loop-guard] stock-data-hub failed to start; log: $HUB_LOG" >&2
  return 3
}

if [ -f "$NOTIFY_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$NOTIFY_ENV_FILE"
  set +a
fi

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

if [ "$PAI_NOTIFY_ON_SUCCESS_OVERRIDE" != "__UNSET__" ]; then
  export PAI_NOTIFY_ON_SUCCESS="$PAI_NOTIFY_ON_SUCCESS_OVERRIDE"
fi

MODE="${1:-sample}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$MODE" in
  sample)
    RUN_LABEL="sample"
    RUN_CMD=("$PYTHON_BIN" "scripts/pai_loop.py")
    ;;
  real)
    RUN_LABEL="real"
    RUN_CMD=("$PYTHON_BIN" "scripts/pai_loop.py" "--with-real-data")
    ;;
  *)
    echo "[pai-loop-guard] invalid mode: $MODE (expected: sample|real)" >&2
    exit 1
    ;;
esac

if [ "$#" -gt 0 ]; then
  RUN_CMD+=("$@")
fi

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log_alert() {
  local line="$1"
  printf '[%s] %s\n' "$(timestamp)" "$line" >> "$ALERT_LOG"
}

send_feishu_text() {
  local message="$1"
  local webhook="${PAI_FEISHU_WEBHOOK_URL:-${FEISHU_BOT_WEBHOOK_URL:-}}"
  if [ -n "$webhook" ]; then
    if ! command -v curl >/dev/null 2>&1; then
      log_alert "[notify-failed] curl not found"
    else
      local payload
      payload="$("$PYTHON_BIN" - "$message" <<'PY'
import json
import sys

msg = sys.argv[1]
print(json.dumps({"msg_type": "text", "content": {"text": msg}}, ensure_ascii=False))
PY
)"
      if curl -sS -m 12 -H 'Content-Type: application/json' -d "$payload" "$webhook" >/dev/null; then
        log_alert "[notify-ok] sent to feishu webhook"
        echo '{"sent": true, "delivery_channel": "webhook"}'
        return 0
      fi
      log_alert "[notify-failed] webhook request failed"
    fi
  fi

  if [ ! -f "$FEISHU_SEND_SCRIPT" ]; then
    if [ -z "$webhook" ]; then
      log_alert "[notify-skipped] webhook not configured and app sender missing"
    else
      log_alert "[notify-failed] app sender missing after webhook failure"
    fi
    return 0
  fi

  local title
  title="$(printf '%s\n' "$message" | head -n1)"
  if [ -z "$title" ]; then
    title="PAI闭环告警"
  fi

  local cmd=("$PYTHON_BIN" "$FEISHU_SEND_SCRIPT" "--title" "$title")
  while IFS= read -r line; do
    if [ -n "$line" ]; then
      cmd+=("--line" "$line")
    fi
  done < <(printf '%s\n' "$message" | tail -n +2)

  local send_out
  local send_rc
  set +e
  send_out="$("${cmd[@]}" 2>&1)"
  send_rc=$?
  set -e
  if [ "$send_rc" -eq 0 ]; then
    log_alert "[notify-ok] sent via feishu app script"
    if [ -n "$send_out" ]; then
      printf '%s\n' "$send_out"
    else
      echo '{"sent": true, "delivery_channel": "app"}'
    fi
  else
    log_alert "[notify-failed] app script rc=$send_rc detail=$(printf '%s\n' "$send_out" | tail -n1)"
  fi
  return 0
}

build_dual_module_message() {
  local json_file="$1"
  local module_key="$2"
  "$PYTHON_BIN" - "$json_file" "$module_key" <<'PY'
import json
import sys

payload = json.loads(open(sys.argv[1], "r", encoding="utf-8").read())
module = payload.get(sys.argv[2]) or {}
title = str(module.get("title") or "").strip()
lines = module.get("message_lines") or []
out = [title] if title else []
for line in lines:
    text = str(line).strip()
    if text:
        out.append(text)
print("\n".join(out))
PY
}

send_split_daily_modules() {
  local modules_json="$LOG_DIR/latest_dual_daily_modules.json"
  local focus_md="$LOG_DIR/latest_focus_daily.md"
  local opportunity_md="$LOG_DIR/latest_opportunity_daily.md"
  local build_log="/tmp/pai_dual_daily_modules.log"

  set +e
  "$PYTHON_BIN" "$ROOT_DIR/scripts/build_dual_daily_modules.py" \
    --top-file "$ROOT_DIR/output/top20_first_batch_opportunities_real.csv" \
    --real-file "$ROOT_DIR/data/opportunities.real.csv" \
    --meta-file "$ROOT_DIR/docs/opportunities_real_data_meta.json" \
    --output-focus-md "$focus_md" \
    --output-opportunity-md "$opportunity_md" \
    --output-json "$modules_json" \
    --opportunity-top "${PAI_OPPORTUNITY_TOP:-10}" \
    --message-top "${PAI_MESSAGE_TOP:-8}" >"$build_log" 2>&1
  local build_rc=$?
  set -e
  if [ "$build_rc" -ne 0 ] || [ ! -f "$modules_json" ]; then
    local detail
    detail="$(tail -n 1 "$build_log" 2>/dev/null || true)"
    log_alert "[dual-modules-build-failed] rc=$build_rc detail=${detail}"
    return 1
  fi

  local focus_msg
  local opportunity_msg
  focus_msg="$(build_dual_module_message "$modules_json" "focus_module")"
  opportunity_msg="$(build_dual_module_message "$modules_json" "opportunity_module")"

  if [ -z "$focus_msg" ] || [ -z "$opportunity_msg" ]; then
    log_alert "[dual-modules-message-empty] json=$modules_json"
    return 1
  fi

  send_feishu_text "$focus_msg"
  send_feishu_text "$opportunity_msg"
  log_alert "[dual-modules-sent] json=$modules_json"
  return 0
}

cleanup() {
  if [ "$HUB_STARTED_BY_GUARD" = "1" ] && [ -n "$HUB_PID" ]; then
    kill "$HUB_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

cd "$ROOT_DIR"
echo "[pai-loop-guard] mode=$RUN_LABEL started_at=$(timestamp)"

rc=0
if [ "$RUN_LABEL" = "real" ]; then
  if ! ensure_hub_ready; then
    rc=$?
  fi
fi

if [ "$rc" -eq 0 ]; then
  set +e
  "${RUN_CMD[@]}"
  rc=$?
  set -e
fi

report_path="$ROOT_DIR/output/pai_loop/latest_report.md"
host_name="$(hostname)"

if [ "$rc" -ne 0 ]; then
  if [ "$rc" -eq 2 ]; then
    reason="步骤失败或漂移告警"
  else
    reason="执行异常"
  fi

  log_alert "[run-failed] mode=$RUN_LABEL rc=$rc reason=$reason report=$report_path"

  alert_text=$'【PAI闭环告警】\n'
  alert_text+=$"模式: ${RUN_LABEL}\n"
  alert_text+=$"状态: ${reason}\n"
  alert_text+=$"退出码: ${rc}\n"
  alert_text+=$"主机: ${host_name}\n"
  alert_text+=$"时间: $(timestamp)\n"
  alert_text+=$"报告: ${report_path}\n"
  alert_text+=$"建议: 先看 latest_report.md 的“失败步骤日志摘要”和“漂移与告警”。"
  send_feishu_text "$alert_text"
  echo "[pai-loop-guard] failed rc=$rc"
  exit "$rc"
fi

if [ "${PAI_NOTIFY_ON_SUCCESS:-0}" = "1" ]; then
  if [ "$RUN_LABEL" = "real" ] && send_split_daily_modules; then
    :
  else
    success_text=$'【PAI闭环成功】\n'
    success_text+=$"模式: ${RUN_LABEL}\n"
    success_text+=$"主机: ${host_name}\n"
    success_text+=$"时间: $(timestamp)\n"
    success_text+=$"报告: ${report_path}"
    send_feishu_text "$success_text"
  fi
fi

echo "[pai-loop-guard] completed mode=$RUN_LABEL rc=0"
