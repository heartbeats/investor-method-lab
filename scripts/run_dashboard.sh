#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8090}"

is_port_free() {
  python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(("0.0.0.0", port))
except OSError:
    print("busy")
    sys.exit(1)
finally:
    s.close()
PY
}

if ! is_port_free "$PORT" >/dev/null 2>&1; then
  echo "[ERROR] 端口 ${PORT} 已被占用。"
  echo "可换端口重试：bash scripts/run_dashboard.sh 8091"
  exit 1
fi

cd "$ROOT_DIR"
echo "[INFO] Investor Method Lab 网页看板启动中..."
echo "[INFO] 打开地址：http://127.0.0.1:${PORT}/web/"
python3 -m http.server "$PORT" --bind 0.0.0.0
