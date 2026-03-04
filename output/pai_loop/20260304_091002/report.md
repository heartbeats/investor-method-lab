# PAI 迭代闭环报告

- run_id: `20260304_091002`
- started_at: `2026-03-04 09:10:02`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.13 |
| `generate_top20_pack_sample` | ok | 0 | 0.23 |
| `build_real_opportunities` | failed | 1 | 11.56 |

## 2) 关键产物快照

| Artifact | Exists | Size | Lines | Changed |
|---|---|---:|---:|---|
| `data/top20_global_investors_verified_ab.json` | True | 47195 | 1182 | no |
| `docs/top20_global_investors_verified_ab.md` | True | 6634 | 26 | no |
| `docs/top20_verification_backlog.md` | True | 145 | 4 | no |
| `docs/top20_opportunity_pack.md` | True | 11969 | 176 | yes |
| `output/top20_first_batch_opportunities.csv` | True | 176778 | 11 | yes |
| `output/top20_methodology_top5_by_group.csv` | True | 13555 | 46 | yes |
| `output/top20_diversified_opportunities.csv` | True | 176840 | 11 | yes |

## 3) 漂移与告警

- 无关键漂移告警。

## 4) 失败步骤日志摘要

### build_real_opportunities

```text
[stderr]
Traceback (most recent call last):
  File "/home/afu/projects/investor-method-lab/scripts/build_real_opportunities.py", line 1371, in <module>
    main()
  File "/home/afu/projects/investor-method-lab/scripts/build_real_opportunities.py", line 1306, in main
    raise RuntimeError("Failed to fetch market data:\n" + "\n".join(failures))
RuntimeError: Failed to fetch market data:
BF.B: BF.B: missing close history from Yahoo Finance
ETR: ETR: missing close history from Yahoo Finance
FI: FI: missing close history from Yahoo Finance
IPG: IPG: missing close history from Yahoo Finance
K: K: missing close history from Yahoo Finance
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。