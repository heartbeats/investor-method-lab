# PAI 迭代闭环报告

- run_id: `20260302_091001`
- started_at: `2026-03-02 09:10:01`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.11 |
| `generate_top20_pack_sample` | ok | 0 | 0.10 |
| `build_real_opportunities` | failed | 1 | 56.62 |

## 2) 关键产物快照

| Artifact | Exists | Size | Lines | Changed |
|---|---|---:|---:|---|
| `data/top20_global_investors_verified_ab.json` | True | 47195 | 1182 | no |
| `docs/top20_global_investors_verified_ab.md` | True | 6634 | 26 | no |
| `docs/top20_verification_backlog.md` | True | 145 | 4 | no |
| `docs/top20_opportunity_pack.md` | True | 10835 | 162 | no |
| `output/top20_first_batch_opportunities.csv` | True | 1142 | 11 | no |
| `output/top20_methodology_top5_by_group.csv` | True | 5701 | 46 | no |
| `output/top20_diversified_opportunities.csv` | True | 1152 | 11 | no |

## 3) 漂移与告警

- 无关键漂移告警。

## 4) 失败步骤日志摘要

### build_real_opportunities

```text
[stderr]
    raise RuntimeError("Failed to fetch market data:\n" + "\n".join(failures))
RuntimeError: Failed to fetch market data:
NVDA: Too Many Requests. Rate limited. Try after a while.
0700.HK: Too Many Requests. Rate limited. Try after a while.
3690.HK: Too Many Requests. Rate limited. Try after a while.
9988.HK: Too Many Requests. Rate limited. Try after a while.
1810.HK: Too Many Requests. Rate limited. Try after a while.
1211.HK: Too Many Requests. Rate limited. Try after a while.
9618.HK: Too Many Requests. Rate limited. Try after a while.
9999.HK: Too Many Requests. Rate limited. Try after a while.
0981.HK: Too Many Requests. Rate limited. Try after a while.
600519.SS: Too Many Requests. Rate limited. Try after a while.
000858.SZ: Too Many Requests. Rate limited. Try after a while.
300750.SZ: Too Many Requests. Rate limited. Try after a while.
600036.SS: Too Many Requests. Rate limited. Try after a while.
601318.SS: Too Many Requests. Rate limited. Try after a while.
600900.SS: Too Many Requests. Rate limited. Try after a while.
002594.SZ: Too Many Requests. Rate limited. Try after a while.
600276.SS: Too Many Requests. Rate limited. Try after a while.
601899.SS: Too Many Requests. Rate limited. Try after a while.
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。