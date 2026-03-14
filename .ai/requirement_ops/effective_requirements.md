# Effective Requirements

Execution should always read this effective view instead of assuming requirements.md has already been merged.
It is generated from the canonical requirements plus active requirement overrides.

<!-- REQUIREMENT_OPS_EFFECTIVE:BEGIN -->
{
  "version": 1,
  "project": "investor-method-lab",
  "generated_at": "2026-03-14T23:26:48.242825+08:00",
  "base_revision": "2026-03-14T23:26:48.242557+08:00",
  "active_change_ids": [],
  "meta_overrides": [],
  "requirements": [
    {
      "requirement_id": "REQ-0002",
      "title": "同一机会包展示机会验真结果与 DCF 估值联动",
      "priority": "P1",
      "base_revision": "2026-03-14T23:26:48.242557+08:00",
      "applied_changes": [],
      "effective_body": "在同一份机会包中同时展示机会验真结果与 DCF/外部估值关键字段，让单个标的的机会、风险、估值能一起解释。",
      "effective_acceptance": [
        "机会包正文至少同时包含机会验真结果、估值来源/区间、关键风险提示。",
        "当 DCF 不可用时，允许降级到 external valuation 或 close，但必须明确标注来源。",
        "统一输出优先复用 `docs/top20_opportunity_pack_real_3markets.md`、`output/opportunity_validation_latest.json` 等现有产物。"
      ],
      "linked_kpis": [
        "关键结论可解释",
        "内容与数据覆盖",
        "产出节奏"
      ],
      "linked_tasks": [
        "TASK-0004",
        "TASK-0005",
        "TASK-0006"
      ]
    },
    {
      "requirement_id": "REQ-0003",
      "title": "机会包补齐字段级来源映射与可信度评分",
      "priority": "P1",
      "base_revision": "2026-03-14T23:26:48.242557+08:00",
      "applied_changes": [],
      "effective_body": "机会验真报表除命中率外，还必须输出字段级来源映射与可信度评分，保证用户能判断每个关键结论来自哪里、可信到什么程度。",
      "effective_acceptance": [
        "关键字段至少覆盖：机会状态、命中率/超额收益、估值来源、核心结论。",
        "每个关键字段都能标注来源系统或回退链路。",
        "可信度评分口径固定，缺失来源时不能伪造高可信分。"
      ],
      "linked_kpis": [
        "关键结论可解释",
        "内容与数据覆盖"
      ],
      "linked_tasks": [
        "TASK-0007",
        "TASK-0008",
        "TASK-0009"
      ]
    },
    {
      "requirement_id": "REQ-0004",
      "title": "人工复核结果回写到 backlog、机会包和 KPI",
      "priority": "P1",
      "base_revision": "2026-03-14T23:26:48.242557+08:00",
      "applied_changes": [],
      "effective_body": "需要把人工复核结果回写到 backlog、机会包和 KPI，并保持本地工件与人工复核证据可追踪。\n\n补充（CHG-0006）：新增并上调核心数据覆盖度为击球区最重要的KPI之一，需要按focus_pool、signal_pool、top50和整体池分层统计覆盖率，需要系统梳理所有API的能力边界、可查范围、免费层限制、频率预算，需要建立每日固定运行的API增量抓取机制，把能合法获取且未入库的数据持续写入本地数据库，核心数据定义为系统实际需要用到的行情、财务、估值校验、宏观与披露数据，并固化成后续日常数据沉淀规则，已经存在且未变化的数据不要重复存储，逐步形成完整数据库",
      "effective_acceptance": [
        "人工复核结果回写后，backlog 或关联工件能够看到对应 review status 与证据引用。",
        "机会包消费人工复核结果后，关键结论或复核状态在正文或附属工件中可见。",
        "KPI 快照消费人工复核结果后，相关指标保留 evidence refs 并能追溯到 review 工件。",
        "外部查看面失败时，不阻断本地 writeback 与证据落盘。",
        "补充要求来自 CHG-0006。"
      ],
      "linked_kpis": [
        "FLOW-WRITEBACK-COMPLETION",
        "RESULT-TRACEABILITY",
        "BIZ-CUSTOM"
      ],
      "linked_tasks": [
        "TASK-0010",
        "TASK-0011",
        "TASK-0012"
      ]
    }
  ]
}
<!-- REQUIREMENT_OPS_EFFECTIVE:END -->

## Summary

- Project: investor-method-lab
- Generated: 2026-03-14T23:26:48.242825+08:00
- Base revision: 2026-03-14T23:26:48.242557+08:00
- Active overrides: None

## Effective Requirements

### REQ-0002 同一机会包展示机会验真结果与 DCF 估值联动

- Priority: P1
- Applied changes: None
- Body: 在同一份机会包中同时展示机会验真结果与 DCF/外部估值关键字段，让单个标的的机会、风险、估值能一起解释。
- Acceptance:
  - 机会包正文至少同时包含机会验真结果、估值来源/区间、关键风险提示。
  - 当 DCF 不可用时，允许降级到 external valuation 或 close，但必须明确标注来源。
  - 统一输出优先复用 `docs/top20_opportunity_pack_real_3markets.md`、`output/opportunity_validation_latest.json` 等现有产物。

### REQ-0003 机会包补齐字段级来源映射与可信度评分

- Priority: P1
- Applied changes: None
- Body: 机会验真报表除命中率外，还必须输出字段级来源映射与可信度评分，保证用户能判断每个关键结论来自哪里、可信到什么程度。
- Acceptance:
  - 关键字段至少覆盖：机会状态、命中率/超额收益、估值来源、核心结论。
  - 每个关键字段都能标注来源系统或回退链路。
  - 可信度评分口径固定，缺失来源时不能伪造高可信分。

### REQ-0004 人工复核结果回写到 backlog、机会包和 KPI

- Priority: P1
- Applied changes: None
- Body: 需要把人工复核结果回写到 backlog、机会包和 KPI，并保持本地工件与人工复核证据可追踪。

补充（CHG-0006）：新增并上调核心数据覆盖度为击球区最重要的KPI之一，需要按focus_pool、signal_pool、top50和整体池分层统计覆盖率，需要系统梳理所有API的能力边界、可查范围、免费层限制、频率预算，需要建立每日固定运行的API增量抓取机制，把能合法获取且未入库的数据持续写入本地数据库，核心数据定义为系统实际需要用到的行情、财务、估值校验、宏观与披露数据，并固化成后续日常数据沉淀规则，已经存在且未变化的数据不要重复存储，逐步形成完整数据库
- Acceptance:
  - 人工复核结果回写后，backlog 或关联工件能够看到对应 review status 与证据引用。
  - 机会包消费人工复核结果后，关键结论或复核状态在正文或附属工件中可见。
  - KPI 快照消费人工复核结果后，相关指标保留 evidence refs 并能追溯到 review 工件。
  - 外部查看面失败时，不阻断本地 writeback 与证据落盘。
  - 补充要求来自 CHG-0006。
