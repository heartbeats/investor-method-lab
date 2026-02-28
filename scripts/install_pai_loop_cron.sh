#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/output/pai_loop"
PYTHON_BIN="${PYTHON_BIN:-python3}"

CRON_BEGIN="# BEGIN pai-loop"
CRON_END="# END pai-loop"

mkdir -p "$LOG_DIR"

build_block() {
  cat <<EOF
$CRON_BEGIN
# 每天样例数据闭环（非真实数据口径）
10 9 * * * cd "$ROOT_DIR" && $PYTHON_BIN scripts/pai_loop.py >> "$LOG_DIR/cron_sample.log" 2>&1
# 每周一/三/五实时数据闭环
25 9 * * 1,3,5 cd "$ROOT_DIR" && $PYTHON_BIN scripts/pai_loop.py --with-real-data >> "$LOG_DIR/cron_real.log" 2>&1
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
  PYTHON_BIN=python3  # override python binary if needed
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
