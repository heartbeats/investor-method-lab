#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from investor_method_lab.requirement_ops_adapters import build_hit_zone_custom_kpi_output


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: requirement_ops_custom_kpi_adapter.py <payload_file>')
    payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    result = build_hit_zone_custom_kpi_output(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
