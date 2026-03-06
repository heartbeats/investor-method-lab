# online vs snapshot 对比报告（2026-03-06）

- 生成时间：2026-03-06 12:46:35
- online 样本：`data/opportunities.real_3markets.csv` + `output/top20_*_real_3markets.csv`
- snapshot 基线：`output/online_vs_snapshot_compare/20260306_122815/snapshot_only/*`
- 说明：本对比仅比较同一规则引擎下的数据来源差异（online 拉取 vs snapshot 读取）。

## 1. 全局覆盖

| 指标 | online | snapshot | 差异 |
|---|---:|---:|---:|
| 股票总数 | 800 | 800 | +0 |
| 失败数（meta.failed_ticker_count） | 0 | 0 | +0 |
| target_mean_price 覆盖 | 82/800 (10.25%) | 82/800 (10.25%) | +0.00pp |
| fallback 明细命中数（valuation_source_detail） | 769 | 769 | +0 |

## 2. 市场分布

| 市场 | online | snapshot |
|---|---:|---:|
| A | 300 (37.5%) | 300 (37.5%) |
| HK | 200 (25.0%) | 200 (25.0%) |
| US | 300 (37.5%) | 300 (37.5%) |

## 3. 估值来源分布（valuation_source）

| source | online | snapshot | 差异 |
|---|---:|---:|---:|
| `close_fallback` | 699 | 699 | +0 |
| `dcf_external_consensus` | 2 | 2 | +0 |
| `dcf_iv_base` | 29 | 29 | +0 |
| `target_mean_price` | 70 | 70 | +0 |

## 4. TopN 机会池变化

- 样本容量：online=10，snapshot=10
- 重叠：10/10
- online 新增：无
- snapshot 独有（online 移除）：无

## 5. 方法论分层变化（top10_by_group_tiered）

| tier | online | snapshot | 差异 |
|---|---:|---:|---:|
| core | 20 | 20 | +0 |
| watch | 35 | 35 | +0 |
| tactical | 42 | 42 | +0 |

- core 层方法组未发生成分变化。

## 6. 结论

- 本次 online 与 snapshot 在结果上基本一致，说明 24h 快照策略在当前数据窗口内可稳定复现。
- 外部估值在部分标的仍有 fallback，需要持续补源（免费优先，付费待审批）。
- 该报告可直接作为后续每次“在线拉取升级”后的标准回归模板。
