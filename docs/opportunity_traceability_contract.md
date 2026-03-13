# 机会字段级来源映射与可信度评分契约

## 目标
- 为 `REQ-0003` 定义第一阶段正式边界：哪些字段必须做字段级来源映射、哪些输出给正文看、哪些输出留在 JSON / 复核队列。
- 明确本项目不再新造一套“可信度评分”系统，而是正式复用现有 `opportunity_trust_chain` 链路。

## 第一阶段范围
第一阶段只覆盖 `REQ-0003` 验收中最关键、且已经在当前机会包链路中出现的四类字段：

1. `机会状态`
   - 对应字段：`validation_status`、`validation_hit`、`validation_days_held`、`validation_primary_excess_return`
   - 主来源：`output/opportunity_validation_positions_latest.json`
   - 展示目标：正文可显示摘要，JSON 保留逐字段来源
2. `命中率 / 超额收益`
   - 对应字段：`validation_hit`、`validation_primary_excess_return`
   - 主来源：`output/opportunity_validation_positions_latest.json`
   - 展示目标：正文摘要 + 复核层证据
3. `估值来源`
   - 对应字段：`valuation_source`、`valuation_source_detail`、`fair_value`、`target_mean_price`、`dcf_iv_base`
   - 主来源：`data/opportunities.real_3markets.csv`
   - 辅助来源：`output/opportunity_signal_ledger_latest.json`、`output/method_decision_trace_real_3markets.json`
4. `核心结论`
   - 对应字段：`best_reason` / `entry_reason_summary`
   - 主来源：`output/method_decision_trace_real_3markets.json` 与机会包 CSV/JSON

## 不在第一阶段范围
- 不把全部公司资料、研报摘要、事件卡片一次性塞进机会包正文
- 不重写 `unified_trust_scoring_standard_v1.json` 等全局标准，只在项目内声明采用关系
- 不要求一次性覆盖所有历史文件回填；第一阶段只要求 latest 产物可用

## 采用的现有系统
第一阶段正式采用以下现有资产作为唯一可信底座：

- 字段映射标准：`/Users/lucas/codex-project/data/unified_field_source_mapping_v1.json`
- 可信度评分标准：`/Users/lucas/codex-project/data/unified_trust_scoring_standard_v1.json`
- 复核工作流标准：`/Users/lucas/codex-project/data/unified_review_workflow_standard_v1.json`
- 来源白名单：`/Users/lucas/codex-project/data/unified_source_whitelist_and_applicability_v1.json`
- 项目执行模块：`src/investor_method_lab/opportunity_trust_chain.py`
- 项目编排脚本：`scripts/build_opportunity_trust_chain.py`

## 正式数据契约
第一阶段的正式工件分三层：

### 1. 正文层
面向日常阅读，保留压缩后的解释结果，不展示全量字段来源：
- `docs/top20_opportunity_pack_real_3markets.md`
- 每个标的显示：`机会验真`、`估值联动`、`风险提示`
- 正文不直接塞入全量 lineage 细节，只保留可读摘要

### 2. 证据层
面向可追踪和审计，作为字段级来源映射的唯一事实层：
- `output/opportunity_field_lineage_latest.json`
- 每条字段记录至少应包含：
  - `signal_id`
  - `ticker`
  - `field_id`
  - `field_value`
  - `source_system`
  - `source_file_or_api`
  - `source_match_type`
  - `observed_provider_tier`
  - `truth_level`
  - `updated_at` / freshness 相关字段
  - `traceability_score`

### 3. 决策层
面向是否正式采用、是否进复核：
- `output/opportunity_confidence_latest.json`
- `output/opportunity_review_queue_latest.json`
- 机会级别最少保留：
  - `trust_score`
  - `trust_grade`
  - `trust_bucket`
  - `review_result`
  - `formal_layer_eligible`
  - `warnings`
  - `hard_veto_reasons`

## 展示层级规则
- 正文：只显示“摘要 + 风险信号”，避免把 source 明细堆满主报告
- 附录/JSON：承接全部字段级 lineage 与可信度证据
- 复核队列：只承接需要人工处理的机会，不和正文混在一起

具体落点：
- 正文继续复用 `docs/top20_opportunity_pack_real_3markets.md`
- 字段级来源映射以 `output/opportunity_field_lineage_latest.json` 为准
- 可信度评分以 `output/opportunity_confidence_latest.json` 为准
- 人工复核以 `output/opportunity_review_queue_latest.json` 为准

## 第一阶段可信度规则
第一阶段不重新设计评分算法，直接沿用现有标准，并固化三条业务解释：
- `close_fallback` 不能进入正式层，默认进入 `D / noisy / manual_escalation`
- `target_mean_price` 这类 reference-only 估值，默认最多进入 `C / watch`，可读但不算正式层
- 只有具备完整 traceability 且满足主源/备源规则的字段，机会才有资格进入 `A/B` 正式层

## 与 REQ-0003 的映射
REQ-0003 当前验收写的是：
- 覆盖关键字段
- 每个关键字段能标注来源系统或回退链路
- 缺失来源时不能伪造高可信分

第一阶段对应关系：
- “关键字段覆盖” -> 先收敛到 4 类字段：机会状态、命中率/超额收益、估值来源、核心结论
- “来源系统或回退链路” -> 统一落在 `opportunity_field_lineage_latest.json`
- “不能伪造高可信分” -> 统一落在 `opportunity_confidence_latest.json` 的 bucket / grade / veto 规则

## 下一步实现指引
`TASK-0008` 开始再做真正的产品化接入，优先级如下：
1. 在三市场主编排里接入 `scripts/build_opportunity_trust_chain.py`
2. 在机会包正文中增加“可信度/来源摘要”轻量展示
3. 把 `field_lineage / confidence / review_queue` 结果与 requirement-ops KPI 关联
4. 仅在需要人工处理时把 `review_queue` 暴露给操作层
