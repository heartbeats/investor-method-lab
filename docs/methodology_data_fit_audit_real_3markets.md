# 方法论数据适配审计（real_3markets）

- 生成时间(UTC)：2026-03-05T22:23:48.790867+00:00
- 样本数：800
- 缓存命中行：800

## 结论

- 方法论执行层所需主字段齐备（price_to_fair_value/6因子分值/DCF惩罚字段可用）。
- 主要缺口不在“有没有字段”，而在“底层证据覆盖差异”：A/HK 分析师与 DCF 覆盖偏低。

## 关键覆盖率

- price_to_fair_value: 800/800 (100.00%)
- quality_score: 800/800 (100.00%)
- growth_score: 800/800 (100.00%)
- momentum_score: 800/800 (100.00%)
- catalyst_score: 800/800 (100.00%)
- risk_score: 800/800 (100.00%)
- certainty_score: 800/800 (100.00%)
- target_mean_price: 751/800 (93.88%)

## 原始证据覆盖（缓存层）

- return_on_equity: 775/800 (96.88%)
- gross_margins: 799/800 (99.88%)
- revenue_growth: 791/800 (98.88%)
- earnings_growth: 682/800 (85.25%)
- analyst_count: 591/800 (73.88%)
- recommendation_mean: 454/800 (56.75%)

## 缺口

- [high] dcf_coverage_low: DCF 覆盖率偏低，会削弱安全边际与质量闸门可信度。
- [medium] a_market_analyst_signal_sparse: A 股分析师维度覆盖不足，导致 catalyst/certainty 更依赖默认值。

## 免费优先动作

- A/HK 基本面优先走 akshare，再回退 yfinance（已接入 stock-data-hub）
- 每日收盘后批量生成本地快照，业务层优先读快照，缺失再回源
- A 股补研报聚合（Eastmoney/akshare），补足 analyst_count 与 recommendation 替代信号

## 低成本付费备选（待决策）

- Tushare Pro | 场景：A 股财务与一致预期补全 | 成本级别：low_to_medium
- FMP Pro | 场景：US/HK 基本面与目标价稳定补源 | 成本级别：low_to_medium
- Polygon/Intrinio | 场景：US 行情/财务高稳定性 | 成本级别：medium
