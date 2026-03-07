#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/output/pai_loop"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PAI_REAL_CRON="${PAI_REAL_CRON:-10 9 * * *}"
TASK_REPORT_SCRIPT="${TASK_REPORT_SCRIPT:-${HOME}/codex-project/scripts/run_task_with_report.sh}"

CRON_BEGIN="# BEGIN pai-loop"
CRON_END="# END pai-loop"

mkdir -p "$LOG_DIR"

build_block() {
  cat <<EOF
$CRON_BEGIN
# 每天跟投（含DCF）主链路（仅 real）
$PAI_REAL_CRON PAI_NOTIFY_ON_SUCCESS=1 PYTHON_BIN="$PYTHON_BIN" bash "$TASK_REPORT_SCRIPT" --task 跟投（含DCF）主链路 --self-notify --report-on failure -- bash "$ROOT_DIR/scripts/pai_loop_guard.sh" real >> "$LOG_DIR/cron_real.log" 2>&1
$CRON_END
EOF
}

strip_block() {
  awk -v begin="$CRON_BEGIN" -v end="$CRON_END" '
    $0 == begin {skip=1; next}
    $0 == end {skip=0; next}
    skip != 1 {print}
  '
}

show_block() {
  awk -v begin="$CRON_BEGIN" -v end="$CRON_END" '
    $0 == begin {print; show=1; next}
    show == 1 {print}
    $0 == end {show=0}
  '
}

apply_cron() {
  local current cleaned merged
  current="$(crontab -l 2>/dev/null || true)"
  cleaned="$(printf '%s\n' "$current" | strip_block)"
  merged="$(printf '%s\n%s\n' "$cleaned" "$(build_block)")"
  printf '%s\n' "$merged" | crontab -
  echo "pai-loop cron installed."
}

remove_cron() {
  local current cleaned
  current="$(crontab -l 2>/dev/null || true)"
  cleaned="$(printf '%s\n' "$current" | strip_block)"
  printf '%s\n' "$cleaned" | crontab -
  echo "pai-loop cron removed."
}

status_cron() {
  local current
  current="$(crontab -l 2>/dev/null || true)"
  if printf '%s\n' "$current" | grep -Fq "$CRON_BEGIN"; then
    echo "pai-loop cron status: installed"
    printf '%s\n' "$current" | show_block
  else
    echo "pai-loop cron status: not installed"
  fi
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/install_pai_loop_cron.sh apply
  bash scripts/install_pai_loop_cron.sh remove
  bash scripts/install_pai_loop_cron.sh status

Env:
  PYTHON_BIN=python3              # override python binary if needed
  PAI_REAL_CRON='10 9 * * *'      # real mode schedule (daily by default)
  PAI_ENV_FILE=/path/to/.env.pai  # optional, env file for guard script
  PAI_NOTIFY_ENV_FILE=...         # optional, fallback app env file
  PAI_FEISHU_SEND_SCRIPT=...      # optional, fallback app sender script
  PAI_FEISHU_WEBHOOK_URL=...      # optional, failed run alert webhook
  FEISHU_BOT_WEBHOOK_URL=...      # optional fallback webhook
  PAI_NOTIFY_ON_SUCCESS=1         # optional, notify success too
EOF
}

ACTION="${1:-status}"
case "$ACTION" in
  apply)
    apply_cron
    status_cron
    ;;
  remove)
    remove_cron
    status_cron
    ;;
  status)
    status_cron
    ;;
  *)
    usage
    exit 1
    ;;
esac
