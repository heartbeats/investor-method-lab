# PAI 迭代闭环报告

- run_id: `20260315_091000`
- started_at: `2026-03-15 09:10:00`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.10 |
| `generate_top20_pack_sample` | ok | 0 | 0.17 |
| `build_real_opportunities` | ok | 0 | 3709.23 |
| `generate_top20_pack_real` | ok | 0 | 1.39 |
| `unit_tests` | failed | 1 | 1.45 |

## 2) 关键产物快照

| Artifact | Exists | Size | Lines | Changed |
|---|---|---:|---:|---|
| `data/top20_global_investors_verified_ab.json` | True | 47195 | 1182 | no |
| `docs/top20_global_investors_verified_ab.md` | True | 6634 | 26 | no |
| `docs/top20_verification_backlog.md` | True | 145 | 4 | no |
| `docs/top20_opportunity_pack.md` | True | 14359 | 176 | no |
| `output/top20_first_batch_opportunities.csv` | True | 198494 | 11 | no |
| `output/top20_methodology_top5_by_group.csv` | True | 13555 | 46 | no |
| `output/top20_diversified_opportunities.csv` | True | 198556 | 11 | no |

## 3) 漂移与告警

- 无关键漂移告警。

## 4) 失败步骤日志摘要

### unit_tests

```text
[stderr]
----------------------------------------------------------------------
ImportError: Failed to import test module: test_seed_dcf_coverage_from_universe
Traceback (most recent call last):
  File "/Users/lucas/.local/share/uv/python/cpython-3.11.15-macos-aarch64-none/lib/python3.11/unittest/loader.py", line 419, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lucas/.local/share/uv/python/cpython-3.11.15-macos-aarch64-none/lib/python3.11/unittest/loader.py", line 362, in _get_module_from_name
    __import__(name)
  File "/Users/lucas/projects/investor-method-lab/tests/test_seed_dcf_coverage_from_universe.py", line 13, in <module>
    SPEC.loader.exec_module(MODULE)
  File "/Users/lucas/projects/investor-method-lab/scripts/seed_dcf_coverage_from_universe.py", line 27, in <module>
    from dcf.financial_ingest import fetch_company_profile_from_yfinance  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ImportError: cannot import name 'fetch_company_profile_from_yfinance' from 'dcf.financial_ingest' (/Users/lucas/projects/hit-zone/dcf/financial_ingest.py)


----------------------------------------------------------------------
Ran 80 tests in 0.042s

FAILED (errors=1)
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。