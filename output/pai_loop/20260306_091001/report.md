# PAI 迭代闭环报告

- run_id: `20260306_091001`
- started_at: `2026-03-06 09:10:01`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.07 |
| `generate_top20_pack_sample` | ok | 0 | 0.15 |
| `build_real_opportunities` | failed | 1 | 191.19 |

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

### build_real_opportunities

```text
[stdout]
[progress] 325/800 cache_hits=0 api_fetches=0 failures=325
[progress] 350/800 cache_hits=0 api_fetches=0 failures=350
[progress] 375/800 cache_hits=0 api_fetches=0 failures=375
[progress] 400/800 cache_hits=0 api_fetches=0 failures=400
[progress] 425/800 cache_hits=0 api_fetches=0 failures=425
[progress] 450/800 cache_hits=0 api_fetches=0 failures=450
[progress] 475/800 cache_hits=1 api_fetches=0 failures=474
[progress] 500/800 cache_hits=1 api_fetches=0 failures=499
[progress] 525/800 cache_hits=3 api_fetches=0 failures=522
[progress] 550/800 cache_hits=3 api_fetches=0 failures=547
[progress] 575/800 cache_hits=3 api_fetches=0 failures=572
[progress] 600/800 cache_hits=3 api_fetches=0 failures=597
[progress] 625/800 cache_hits=3 api_fetches=0 failures=622
[progress] 650/800 cache_hits=3 api_fetches=0 failures=647
[progress] 675/800 cache_hits=3 api_fetches=0 failures=672
[progress] 700/800 cache_hits=3 api_fetches=0 failures=697
[progress] 725/800 cache_hits=3 api_fetches=0 failures=722
[progress] 750/800 cache_hits=3 api_fetches=0 failures=747
[progress] 775/800 cache_hits=3 api_fetches=0 failures=772
[progress] 800/800 cache_hits=3 api_fetches=0 failures=797
[stderr]
KIM: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
KMI: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
KKR: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
KLAC: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
KHC: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
KR: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LHX: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LH: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LRCX: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LW: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LVS: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LDOS: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LEN: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LII: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LLY: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LIN: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LYV: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LMT: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
L: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
LOW: IML_STOCK_DATA_HUB_URL is missing in Hub-Only mode
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。