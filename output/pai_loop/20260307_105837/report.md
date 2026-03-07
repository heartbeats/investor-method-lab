# PAI 迭代闭环报告

- run_id: `20260307_105837`
- started_at: `2026-03-07 10:58:37`
- with_real_data: `False`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.03 |
| `generate_top20_pack_sample` | ok | 0 | 0.04 |
| `unit_tests` | ok | 0 | 0.30 |

## 2) 关键产物快照

| Artifact | Exists | Size | Lines | Changed |
|---|---|---:|---:|---|
| `data/top20_global_investors_verified_ab.json` | True | 47195 | 1182 | no |
| `docs/top20_global_investors_verified_ab.md` | True | 6634 | 26 | no |
| `docs/top20_verification_backlog.md` | True | 145 | 4 | no |
| `docs/top20_opportunity_pack.md` | True | 11969 | 176 | no |
| `output/top20_first_batch_opportunities.csv` | True | 198494 | 11 | no |
| `output/top20_methodology_top5_by_group.csv` | True | 13555 | 46 | no |
| `output/top20_diversified_opportunities.csv` | True | 198556 | 11 | no |

## 3) 漂移与告警

- 无关键漂移告警。

## 4) 失败步骤日志摘要

- 无失败步骤。
## 5) 下一步建议

- 本轮可进入下一次迭代，继续用同一参数跑增量更新。