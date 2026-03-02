#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/output/pai_loop"
ALERT_LOG="$LOG_DIR/alert.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_FILE="${PAI_ENV_FILE:-$ROOT_DIR/.env.pai}"
NOTIFY_ENV_FILE="${PAI_NOTIFY_ENV_FILE:-$HOME/.config/dcf_notify.env}"
FEISHU_SEND_SCRIPT="${PAI_FEISHU_SEND_SCRIPT:-/home/afu/codex-project/scripts/send_feishu_text_message.py}"

mkdir -p "$LOG_DIR"

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
  else
    log_alert "[notify-failed] app script rc=$send_rc detail=$(printf '%s\n' "$send_out" | tail -n1)"
  fi
  return 0
}

cd "$ROOT_DIR"
echo "[pai-loop-guard] mode=$RUN_LABEL started_at=$(timestamp)"

set +e
"${RUN_CMD[@]}"
rc=$?
set -e

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
  success_text=$'【PAI闭环成功】\n'
  success_text+=$"模式: ${RUN_LABEL}\n"
  success_text+=$"主机: ${host_name}\n"
  success_text+=$"时间: $(timestamp)\n"
  success_text+=$"报告: ${report_path}"
  send_feishu_text "$success_text"
fi

echo "[pai-loop-guard] completed mode=$RUN_LABEL rc=0"
