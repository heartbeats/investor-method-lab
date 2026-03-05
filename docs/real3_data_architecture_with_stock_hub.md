# real_3markets 数据架构（联动 stock-data-hub）

更新时间：2026-03-05

## 1. 结论先行

- 方法论 V4 当前“执行字段”已可用，但底层证据覆盖并不均衡。
- 主缺口在 A/HK 的分析师维度与 DCF 覆盖，不在打分引擎本身。
- 推荐架构：`stock-data-hub` 统一取数 + 每日本地快照 + `investor-method-lab` 因子与方法论执行。

## 2. 当前匹配度（审计结果）

来源：`docs/methodology_data_fit_audit_real_3markets.json`

- 方法论执行字段覆盖：
  - `price_to_fair_value/quality/growth/momentum/catalyst/risk/certainty` = 100%
- 关键证据覆盖：
  - `target_mean_price`：70.0%（A 34.3% / HK 80.0% / US 99.0%）
  - `analyst_count`：70.0%（A 34.3% / HK 80.0% / US 99.0%）
  - `recommendation_mean`：56.8%（A 28.3% / HK 42.5% / US 94.7%）
  - DCF 覆盖：3.75%（IV 覆盖 3.63%）

## 3. 目标架构（分层）

1. 数据接入层（`stock-data-hub`）
- 统一封装 yfinance/akshare/futu/fmp/alpha_vantage。
- A/HK 基本面链路：`akshare -> yfinance`（已落地）。

2. 本地快照层（`stock-data-hub/data_lake`）
- 每日收盘后批量拉取三域：
  - `quotes`
  - `fundamentals`
  - `external_valuations`
- 落盘：
  - `data_lake/snapshots/dt=YYYY-MM-DD/*.jsonl`
  - `manifest.json`

3. 特征层（`investor-method-lab`）
- 读取当日快照，优先快照，缺失再回源 hub。
- 输出 `opportunities.real_3markets.csv` 及 meta。

4. 策略层（方法论 V4）
- 规则引擎仅消费标准化因子与解释轨迹。
- 不直接依赖任何单一外部 provider。

## 4. 频率策略（降频且可用）

- `quotes`：每日收盘后全量 1 次；盘中只对候选池增量刷新。
- `fundamentals`：每日 1 次，财报季可升到每日 2 次。
- `external_valuations`：每日 1 次。
- 对失败 symbol 做白名单补拉，不做全市场反复重试。

## 5. 缺口与补源动作

已落地：

- A/HK 基本面新增 akshare 路由（free）。
- 本地快照落盘脚本：
  - `/home/afu/projects/stock-data-hub/scripts/build_local_stock_snapshot.py`

待落地（free-first）：

- A 股研报聚合（Eastmoney/akshare）补分析师信号与目标价统计。
- DCF 覆盖扩容（优先核心池高权重标的）。

待你决策（低成本付费）：

- `data/source_upgrade_backlog.json`

## 6. 执行顺序（建议）

1. 先固定每日快照任务（收盘后）。
2. 在 `build_real_opportunities.py` 增加“优先读快照”输入层。
3. 完成 A 股研报聚合补源。
4. 再评估是否引入低成本付费源。

