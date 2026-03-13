# 击球区 M5：估值源补强与多源研究闭环计划

更新时间：2026-03-13

## 1. 当前事实基线

以 `output/valuation_coverage_latest.json`、`output/opportunity_signal_ledger_latest.json` 和 `data/source_upgrade_backlog.json` 为当前事实源，截至 2026-03-12：

- `signal_pool` 当前按 `latest_signal_per_ticker` 口径统计
- `signal_pool` 共 19 个标的，`reference_only=19`，`price_fallback=0`
- `overall_real` 的 `price_fallback` 已从 87.38% 降到 25.25%
- `signal_refresh_reissue` 已成功把 4 个 US 旧信号从历史 `close_fallback` 重发为当前 `target_mean_price`
- 当前 signal pool 已不存在 active `price_fallback`，主瓶颈收敛为：**reference_only -> formal_core / formal_support**

这意味着 M5 现在已经分成两段：

1. **已完成段**：把“历史 signal 来源陈旧”从“当前仍缺源”里剥离出来，并自动重发
2. **待推进段**：继续把 `reference_only` 往正式层推进

## 2. 已实现机制

### 机制 A：`signal_refresh_reissue`

已落地内容：

- 在 `signal_ledger` builder 中自动比较“最新历史 signal 来源”与“当前 real 来源”
- 当当前 `real` 来源支持层级更高时，自动追加一条 refresh reissue signal
- 保留历史 signal，不篡改旧记录
- `valuation_coverage` 改为按每个 ticker 的最新 signal 统计 active signal pool

本轮自动重发成功：

- `AES`
- `BLDR`
- `BXP`
- `F`

结果：

- 这 4 个标的从 active signal pool 的 `price_fallback` 中移除
- active signal pool 当前全部是 `reference_only`

### 机制 B：`valuation_upgrade_backlog`

已落地内容：

- 自动区分 `signal来源` 与 `real来源`
- 自动区分 `signal_refresh_reissue`、`dcf_focus_expansion`、`formalization_review`
- 主流水线每次刷新后自动生成：
  - `data/source_upgrade_backlog.json`
  - `output/valuation_upgrade_backlog_latest.md`

## 3. 当前主目标

### 核心目标

把 active `signal_pool` 从：

- 当前：`reference_only=19`

推进到下一阶段目标：

- 第一目标：`formal_core >= 6`
- 第二目标：`formal_support >= 4`
- 第三目标：A 股高优先级标的不再停留在 `target_mean_price + dcf_symbol_unavailable`

### 验收口径

1. `output/valuation_coverage_latest.md` 能反映 support tier 的真实变化
2. `data/source_upgrade_backlog.json` 只保留真正还需要补强的 active gap
3. `scripts/run_real_pack_3markets.sh` 每次刷新后都会自动生成 ledger refresh + backlog
4. 至少 6 个 A 股标的升级到 `formal_core`

## 4. 当前分通道策略

### 通道 A：`dcf_focus_expansion`

适用对象：A/HK 的 `reference_only` 标的，且 `valuation_source_detail` 含 `dcf_symbol_unavailable`

当前规模：15 个

代表标的：

- `000063.SZ`
- `002241.SZ`
- `600000.SS`
- `600029.SS`
- `600660.SS`
- `600919.SS`
- `601136.SS`
- `601166.SS`
- `601169.SS`
- `601229.SS`
- `601288.SS`
- `601688.SS`
- `601818.SS`
- `688126.SS`
- `688506.SS`

动作：

1. 先用独立批次清单补 DCF 种子与财报（避免直接污染已确认的 7 只特别关注池）
2. 当前首批清单：`data/dcf_focus_expansion_batch1_2026-03-13.csv`
3. 刷新 DCF 取值链路
4. 验收通过后，再决定是否并入 `data/dcf_special_focus_list.json`
5. 目标把 `target_mean_price -> dcf_iv_base`

预期结果：`reference_only -> formal_core`

### 通道 B：`formalization_review`

适用对象：US 标的当前已从历史 fallback 刷新为 `target_mean_price`，但仍只是 `reference_only`

当前规模：4 个

标的：

- `AES`
- `BLDR`
- `BXP`
- `F`

动作：

1. 评估是否存在可稳定接入的 `formal_support` 来源
2. 若没有，就保留 `reference_only`，不再误判成 P0 缺源
3. 后续只在确有稳定外部正式估值源时再升级

预期结果：`reference_only -> formal_support`（若无稳定源，则维持 `reference_only`）

## 5. 执行顺序

### Phase 1（当前）

- 优先做 `dcf_focus_expansion`
- 先从 15 个 A 股 `reference_only` 标的里挑最值得补的第一批

### Phase 2（随后）

- 复核 `AES / BLDR / BXP / F` 是否值得升到 `formal_support`
- 若没有稳定正式源，则不再投入 P0 优先级

## 6. 当前事实源

- 信号账本摘要：`output/opportunity_signal_ledger_latest.json`
- 信号账本 Markdown：`output/opportunity_signal_ledger_latest.md`
- 估值覆盖：`output/valuation_coverage_latest.json`
- 估值覆盖 Markdown：`output/valuation_coverage_latest.md`
- 估值补强 backlog：`data/source_upgrade_backlog.json`
- backlog Markdown：`output/valuation_upgrade_backlog_latest.md`

## 7. 下一步

下一轮直接进入 `dcf_focus_expansion` 第一批实现：

1. 先挑 3-5 个 A 股 `reference_only` 标的补 `dcf_symbol`
2. 更新 `data/dcf_special_focus_list.json`
3. 重跑主流水线，确认 active signal pool 开始出现 `formal_core`

## 8. 2026-03-13 实施结果（Batch 1 + Batch 2）

### 已完成

- 已新增两批 A 股 DCF 扩容清单：
  - `data/dcf_focus_expansion_batch1_2026-03-13.csv`
  - `data/dcf_focus_expansion_batch2_2026-03-13.csv`
- 已成功播种并验收 10 只 A 股：
  - Batch 1：`000063.SZ`、`002241.SZ`、`600000.SS`、`600029.SS`、`601136.SS`
  - Batch 2：`600660.SS`、`601169.SS`、`601229.SS`、`601288.SS`、`601688.SS`
- 10 只均已完成：`company seed -> financial snapshot -> approved valuation -> real row overlay -> signal refresh reissue`

### 机制修复

- `scripts/seed_dcf_coverage_from_universe.py`
  - 新增 A 股 `ths_company_profile` 回退，解决 `yfinance` 限流导致“有 THS 财报、却建不出 company seed”的卡点
- `scripts/update_opportunity_signal_ledger.py`
  - 修复“当前批次已存在同 ID 历史信号时，会错误挡住 refresh reissue”的问题
- `scripts/run_real_pack_3markets.sh`
  - 修复 macOS Bash 3 下空数组在 `set -u` 场景触发 `SNAPSHOT_DATE_ARGS` 报错的问题

### 最新结果

- `signal_pool`：`formal_core 0 -> 10`，`reference_only 19 -> 9`
- `signal_pool formal_valuation_coverage_rate`：`0.00% -> 52.63%`
- `gap_count`：`19 -> 9`
- 当前剩余 backlog：
  - `dcf_focus_expansion = 5`
  - `formalization_review = 4`

### 剩余清单

#### 当前仍需继续推进的 A 股

- `600515.SS`

当前 A 股剩余问题，已经被批处理拆成两类：

- `688126.SS`：DCF company / snapshot / valuation 已补齐，但 `iv_base <= 0`，当前不宜升格到 `dcf_iv_base`
- `600515.SS`：当前仍属 `structural_dcf_base_batch`，本质是 company seed / DCF base 结构性缺口
- `688506.SS`：已通过 `snapshot_seed_batch` 批处理补齐，real row 已升级到 `dcf_iv_base`

### 下一步

1. 先把 `600515.SS` 作为新的 A 股结构性批次处理对象，不再按单票零敲碎打
2. `688126.SS` 继续保留 `reference_only`，只补做 external consensus / 规则例外复核，不再强推 `formal_core`
3. 再进入 `AES / BLDR / BXP / F` 的 `formalization_review`，确认是否存在稳定 `formal_support`

## 9. 2026-03-13 实施结果（Batch 3 / 批处理版）

### 本轮完成

- 不再按 5 个 5 个手工挑；改为直接按“异常类型”批处理
- 已把 3 只 A 股银行类缺口一次性切到 runtime RI shell：
  - `600919.SS`
  - `601166.SS`
  - `601818.SS`
- 已把这 3 只从 `target_mean_price` 批量升级到 `dcf_iv_base`
- 已重刷：
  - `output/opportunity_signal_ledger_latest.json`
  - `output/opportunity_validation_latest.json`
  - `output/opportunity_field_lineage_latest.json`
  - `output/valuation_coverage_latest.json`
  - `data/source_upgrade_backlog.json`

### 当前最新结果

以 `output/valuation_coverage_latest.json` 与 `data/source_upgrade_backlog.json` 为准：

- `signal_pool.count = 20`
- `signal_pool.valuation_source_breakdown = {dcf_iv_base: 14, target_mean_price: 6}`
- `signal_pool.valuation_support_breakdown = {formal_core: 14, reference_only: 6}`
- `signal_pool.formal_valuation_coverage_rate = 70%`
- `focus_pool.count = 7` 且 `focus_pool.formal_valuation_coverage_rate = 100%`
- backlog 已收敛到 `6` 条：
  - `dcf_focus_expansion = 2`
  - `formalization_review = 4`

### 关键判断

剩余缺口已经不是同一类问题：

1. `600919 / 601166 / 601818`
   - 问题不是“数据抓不到”，而是原先卡在 company seed / DCF 准入入口
   - 现在已通过 runtime RI shell 批量放行，不再需要逐只手工补

2. `688126`
   - 已经完成 company seed、approved snapshot 与 valuation
   - 但最新 `iv_base <= 0`，当前不会被 real overlay 升格到 `dcf_iv_base`
   - 这不是“没数据”，而是 **DCF 结果本身不可用作正 fair value**

3. `688506`
   - 已经通过 `snapshot_seed_batch` 批处理补齐 approved snapshot 与 valuation
   - 采用 `5Y mean + relaxed peak guard` 的批处理归一化后，`iv_base = 49.02`
   - real row 已升级到 `dcf_iv_base`，并触发 `signal_refresh_reissue`

### 下一步

- `600515.SS` 接替成为当前唯一的 A 股结构性批次
- `688126.SS` 继续保留 `reference_only`，仅复核是否存在 external consensus 或规则例外
- `AES / BLDR / BXP / F` 维持 `formalization_review`，后续只在找到稳定正式源时再升级
