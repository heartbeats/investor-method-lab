#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.requirement_ops_adapters import execute_hit_zone_project_writeback


def main() -> int:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        raise SystemExit('usage: requirement_ops_project_writeback_adapter.py <payload_file> [--dry-run]')
    payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    dry_run = len(sys.argv) == 3 and sys.argv[2] == '--dry-run'
    result = execute_hit_zone_project_writeback(payload, dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
