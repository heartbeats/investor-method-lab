from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_opportunity_validation.py"

spec = importlib.util.spec_from_file_location("build_opportunity_validation", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
infer_validation_as_of_date = module.infer_validation_as_of_date


class BuildOpportunityValidationScriptTest(unittest.TestCase):
    def test_infer_validation_as_of_date_prefers_newer_signal_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            meta_file = Path(tmp_dir) / "meta.json"
            meta_file.write_text(json.dumps({"as_of_dates": ["2026-03-12"]}, ensure_ascii=False), encoding="utf-8")
            signals = [
                {"ticker": "BLDR", "as_of_date": "2026-03-14"},
                {"ticker": "F", "as_of_date": "2026-03-14"},
            ]
            result = infer_validation_as_of_date(meta_file, signals=signals)
        self.assertEqual(result, "2026-03-14")


if __name__ == "__main__":
    unittest.main()
