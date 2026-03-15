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
echo "[INFO] Investor Method Lab 历史参考页服务启动中..."
echo "[INFO] 默认主页请使用击球区：http://127.0.0.1:8000/"
echo "[INFO] 当前 8090 仅保留历史页："
echo "[INFO] - 首页跳转页：http://127.0.0.1:${PORT}/web/"
echo "[INFO] - 历史投资人详情：http://127.0.0.1:${PORT}/web/investor.html?id=warren_buffett"
echo "[INFO] - 历史数据口径页：http://127.0.0.1:${PORT}/web/data-info.html"
python3 -m http.server "$PORT" --bind 0.0.0.0
