# PAI 迭代闭环报告

- run_id: `20260318_091000`
- started_at: `2026-03-18 09:10:00`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.11 |
| `generate_top20_pack_sample` | ok | 0 | 0.15 |
| `build_real_opportunities` | failed | 1 | 2343.94 |

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

### build_real_opportunities

```text
[stdout]
[progress] 325/800 cache_hits=0 api_fetches=0 failures=325
[progress] 350/800 cache_hits=0 api_fetches=0 failures=350
[progress] 375/800 cache_hits=0 api_fetches=0 failures=375
[progress] 400/800 cache_hits=0 api_fetches=0 failures=400
[progress] 425/800 cache_hits=0 api_fetches=0 failures=425
[progress] 450/800 cache_hits=0 api_fetches=0 failures=450
[progress] 475/800 cache_hits=0 api_fetches=0 failures=475
[progress] 500/800 cache_hits=0 api_fetches=0 failures=500
[progress] 525/800 cache_hits=0 api_fetches=0 failures=525
[progress] 550/800 cache_hits=0 api_fetches=0 failures=550
[progress] 575/800 cache_hits=0 api_fetches=0 failures=575
[progress] 600/800 cache_hits=0 api_fetches=0 failures=600
[progress] 625/800 cache_hits=0 api_fetches=0 failures=625
[progress] 650/800 cache_hits=0 api_fetches=0 failures=650
[progress] 675/800 cache_hits=0 api_fetches=0 failures=675
[progress] 700/800 cache_hits=0 api_fetches=0 failures=700
[progress] 725/800 cache_hits=0 api_fetches=0 failures=725
[progress] 750/800 cache_hits=0 api_fetches=0 failures=750
[progress] 775/800 cache_hits=0 api_fetches=0 failures=775
[progress] 800/800 cache_hits=0 api_fetches=0 failures=800
[stderr]
KMB: name 'normalize_text' is not defined
KIM: name 'normalize_text' is not defined
KMI: name 'normalize_text' is not defined
KKR: name 'normalize_text' is not defined
KLAC: name 'normalize_text' is not defined
KHC: name 'normalize_text' is not defined
KR: name 'normalize_text' is not defined
LHX: name 'normalize_text' is not defined
LH: name 'normalize_text' is not defined
LRCX: name 'normalize_text' is not defined
LW: name 'normalize_text' is not defined
LVS: name 'normalize_text' is not defined
LDOS: name 'normalize_text' is not defined
LEN: name 'normalize_text' is not defined
LII: name 'normalize_text' is not defined
LLY: name 'normalize_text' is not defined
LIN: name 'normalize_text' is not defined
LYV: name 'normalize_text' is not defined
LMT: name 'normalize_text' is not defined
L: name 'normalize_text' is not defined
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。