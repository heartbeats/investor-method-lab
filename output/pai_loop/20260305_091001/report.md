# PAI 迭代闭环报告

- run_id: `20260305_091001`
- started_at: `2026-03-05 09:10:01`
- with_real_data: `True`
- skip_tests: `False`

## 1) 执行步骤

| Step | Status | RC | Duration(s) |
|---|---|---:|---:|
| `build_verified_investors` | ok | 0 | 0.17 |
| `generate_top20_pack_sample` | ok | 0 | 0.37 |
| `build_real_opportunities` | failed | 1 | 2440.75 |

## 2) 关键产物快照

| Artifact | Exists | Size | Lines | Changed |
|---|---|---:|---:|---|
| `data/top20_global_investors_verified_ab.json` | True | 47195 | 1182 | no |
| `docs/top20_global_investors_verified_ab.md` | True | 6634 | 26 | no |
| `docs/top20_verification_backlog.md` | True | 145 | 4 | no |
| `docs/top20_opportunity_pack.md` | True | 11969 | 176 | no |
| `output/top20_first_batch_opportunities.csv` | True | 198494 | 11 | yes |
| `output/top20_methodology_top5_by_group.csv` | True | 13555 | 46 | no |
| `output/top20_diversified_opportunities.csv` | True | 198556 | 11 | yes |

## 3) 漂移与告警

- 无关键漂移告警。

## 4) 失败步骤日志摘要

### build_real_opportunities

```text
[stdout]
[progress] 75/800 cache_hits=53 api_fetches=0 failures=22
[progress] 100/800 cache_hits=53 api_fetches=0 failures=47
[progress] 125/800 cache_hits=53 api_fetches=0 failures=72
[progress] 150/800 cache_hits=53 api_fetches=0 failures=97
[progress] 175/800 cache_hits=53 api_fetches=0 failures=122
[progress] 200/800 cache_hits=53 api_fetches=0 failures=147
[progress] 225/800 cache_hits=53 api_fetches=0 failures=172
[progress] 275/800 cache_hits=70 api_fetches=0 failures=205
[progress] 300/800 cache_hits=82 api_fetches=0 failures=218
[progress] 325/800 cache_hits=100 api_fetches=0 failures=225
[progress] 350/800 cache_hits=114 api_fetches=0 failures=236
[progress] 425/800 cache_hits=143 api_fetches=0 failures=282
[progress] 475/800 cache_hits=170 api_fetches=0 failures=305
[progress] 500/800 cache_hits=183 api_fetches=0 failures=317
[skip] BF.B: known delisted/unavailable
[progress] 600/800 cache_hits=242 api_fetches=0 failures=357
[progress] 675/800 cache_hits=279 api_fetches=0 failures=395
[progress] 700/800 cache_hits=288 api_fetches=0 failures=411
[progress] 775/800 cache_hits=334 api_fetches=0 failures=440
[stderr]
IEX: IEX: missing close history from Yahoo Finance
IDXX: IDXX: missing close history from Yahoo Finance
IR: IR: missing close history from Yahoo Finance
IBKR: IBKR: missing close history from Yahoo Finance
INTU: INTU: missing close history from Yahoo Finance
IVZ: IVZ: missing close history from Yahoo Finance
INVH: INVH: missing close history from Yahoo Finance
IRM: IRM: missing close history from Yahoo Finance
JBHT: JBHT: missing close history from Yahoo Finance
JKHY: JKHY: missing close history from Yahoo Finance
JCI: JCI: missing close history from Yahoo Finance
KDP: KDP: missing close history from Yahoo Finance
KEYS: KEYS: missing close history from Yahoo Finance
KMB: KMB: missing close history from Yahoo Finance
KIM: KIM: missing close history from Yahoo Finance
KMI: KMI: fetch timeout>25.0s
LDOS: LDOS: missing close history from Yahoo Finance
LEN: LEN: missing close history from Yahoo Finance
LIN: LIN: missing close history from Yahoo Finance
L: L: missing close history from Yahoo Finance
```

## 5) 下一步建议

- 先修复失败步骤后再执行下一轮，避免脏状态放大。