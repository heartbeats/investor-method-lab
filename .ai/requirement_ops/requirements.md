# Requirements

Canonical local source of truth for requirement-ops.
Keep the embedded JSON block authoritative; the human-readable sections below are rendered from it.

<!-- REQUIREMENT_OPS:BEGIN -->
{
  "version": 1,
  "project": "investor-method-lab",
  "updated_at": "2026-03-14T23:26:48.242557+08:00",
  "goal": "稳定产出可审阅、可追踪的真实数据机会包，并把机会验真结果与 DCF/外部估值联动进同一份机会包，支撑每日研究判断。",
  "target_users": [
    "Lucas（主审阅者 / 决策辅助使用者）",
    "围绕机会包做日更研究的投资研究者"
  ],
  "core_problem": "机会验真、估值联动和数据来源分散在多条输出中，导致同一标的的机会、风险、估值难以在一个包里解释清楚。",
  "non_goals": [
    "不直接生成交易指令或自动下单。",
    "不把样本数据或无法追溯来源的数据当成生产口径。",
    "不承诺所有估值源都实时可用；上游缺失时允许降级展示。"
  ],
  "constraints": [
    "主链路以真实数据为先，允许在数据源失败时降级到可解释的替代口径。",
    "机会包需要兼容三市场输出节奏，并尽量复用现有 `run_real_pack_3markets.sh` 产物。",
    "DCF、外部估值、机会验真、来源映射都必须保留字段级可追踪性。"
  ],
  "open_questions": [
    "统一机会包中，机会验真与估值联动块的最终排序与展示层级是否固定为“机会 -> 估值 -> 风险 -> 来源”。",
    "字段级来源映射与可信度评分应展示在正文、附录，还是单独 JSON/表格。"
  ],
  "decision_log": [
    {
      "timestamp": "2026-03-13T10:08:13.920305+08:00",
      "type": "auto_merge",
      "change_ids": [
        "CHG-0001",
        "CHG-0002"
      ],
      "created_requirement_ids": [
        "REQ-0001",
        "REQ-0002"
      ],
      "updated_requirement_ids": []
    },
    {
      "timestamp": "2026-03-13T10:08:13.984279+08:00",
      "type": "auto_merge",
      "change_ids": [
        "CHG-0003"
      ],
      "created_requirement_ids": [
        "REQ-0003"
      ],
      "updated_requirement_ids": [
        "REQ-0001"
      ]
    },
    {
      "timestamp": "2026-03-13T12:12:24.690979+08:00",
      "type": "auto_merge",
      "change_ids": [
        "CHG-0004"
      ],
      "created_requirement_ids": [
        "REQ-0004"
      ],
      "updated_requirement_ids": []
    },
    {
      "timestamp": "2026-03-14T22:38:51.934629+08:00",
      "type": "auto_merge",
      "change_ids": [
        "CHG-0006"
      ],
      "created_requirement_ids": [],
      "updated_requirement_ids": [
        "REQ-0004"
      ]
    }
  ],
  "requirements": [
    {
      "id": "REQ-0001",
      "title": "维护击球区 M2 机会验真 latest 报表，输出 o",
      "body": "需要维护击球区 M2 机会验真 latest 报表，输出 open/closed/expired、方法组超额收益和命中率。",
      "priority": "P1",
      "status": "superseded",
      "acceptance": [
        "实现并验证：维护击球区 M2 机会验真 latest 报表，输出 o",
        "结果回写到任务系统与 KPI 快照。"
      ],
      "linked_tasks": [],
      "linked_kpis": [
        "RESULT-TRACEABILITY"
      ],
      "source_change_ids": [
        "CHG-0001"
      ],
      "superseded_by": [
        "CHG-0003",
        "REQ-0003"
      ],
      "last_updated": "2026-03-13T10:08:13.984072+08:00"
    },
    {
      "id": "REQ-0002",
      "title": "同一机会包展示机会验真结果与 DCF 估值联动",
      "body": "在同一份机会包中同时展示机会验真结果与 DCF/外部估值关键字段，让单个标的的机会、风险、估值能一起解释。",
      "priority": "P1",
      "status": "active",
      "acceptance": [
        "机会包正文至少同时包含机会验真结果、估值来源/区间、关键风险提示。",
        "当 DCF 不可用时，允许降级到 external valuation 或 close，但必须明确标注来源。",
        "统一输出优先复用 `docs/top20_opportunity_pack_real_3markets.md`、`output/opportunity_validation_latest.json` 等现有产物。"
      ],
      "linked_tasks": [
        "TASK-0004",
        "TASK-0005",
        "TASK-0006"
      ],
      "linked_kpis": [
        "关键结论可解释",
        "内容与数据覆盖",
        "产出节奏"
      ],
      "source_change_ids": [
        "CHG-0002"
      ],
      "superseded_by": [],
      "last_updated": "2026-03-13T14:54:43.929393+08:00"
    },
    {
      "id": "REQ-0003",
      "title": "机会包补齐字段级来源映射与可信度评分",
      "body": "机会验真报表除命中率外，还必须输出字段级来源映射与可信度评分，保证用户能判断每个关键结论来自哪里、可信到什么程度。",
      "priority": "P1",
      "status": "active",
      "acceptance": [
        "关键字段至少覆盖：机会状态、命中率/超额收益、估值来源、核心结论。",
        "每个关键字段都能标注来源系统或回退链路。",
        "可信度评分口径固定，缺失来源时不能伪造高可信分。"
      ],
      "linked_tasks": [
        "TASK-0007",
        "TASK-0008",
        "TASK-0009"
      ],
      "linked_kpis": [
        "关键结论可解释",
        "内容与数据覆盖"
      ],
      "source_change_ids": [
        "CHG-0003"
      ],
      "superseded_by": [],
      "last_updated": "2026-03-13T14:54:43.929393+08:00"
    },
    {
      "id": "REQ-0004",
      "title": "人工复核结果回写到 backlog、机会包和 KPI",
      "body": "需要把人工复核结果回写到 backlog、机会包和 KPI，并保持本地工件与人工复核证据可追踪。\n\n补充（CHG-0006）：新增并上调核心数据覆盖度为击球区最重要的KPI之一，需要按focus_pool、signal_pool、top50和整体池分层统计覆盖率，需要系统梳理所有API的能力边界、可查范围、免费层限制、频率预算，需要建立每日固定运行的API增量抓取机制，把能合法获取且未入库的数据持续写入本地数据库，核心数据定义为系统实际需要用到的行情、财务、估值校验、宏观与披露数据，并固化成后续日常数据沉淀规则，已经存在且未变化的数据不要重复存储，逐步形成完整数据库",
      "priority": "P1",
      "status": "active",
      "acceptance": [
        "人工复核结果回写后，backlog 或关联工件能够看到对应 review status 与证据引用。",
        "机会包消费人工复核结果后，关键结论或复核状态在正文或附属工件中可见。",
        "KPI 快照消费人工复核结果后，相关指标保留 evidence refs 并能追溯到 review 工件。",
        "外部查看面失败时，不阻断本地 writeback 与证据落盘。",
        "补充要求来自 CHG-0006。"
      ],
      "linked_tasks": [
        "TASK-0010",
        "TASK-0011",
        "TASK-0012"
      ],
      "linked_kpis": [
        "FLOW-WRITEBACK-COMPLETION",
        "RESULT-TRACEABILITY",
        "BIZ-CUSTOM"
      ],
      "source_change_ids": [
        "CHG-0004",
        "CHG-0006"
      ],
      "superseded_by": [],
      "last_updated": "2026-03-14T22:38:51.934621+08:00"
    }
  ]
}
<!-- REQUIREMENT_OPS:END -->

## Summary

- Project: investor-method-lab
- Updated: 2026-03-14T23:26:48.242557+08:00
- Goal: 稳定产出可审阅、可追踪的真实数据机会包，并把机会验真结果与 DCF/外部估值联动进同一份机会包，支撑每日研究判断。
- Target users: Lucas（主审阅者 / 决策辅助使用者）, 围绕机会包做日更研究的投资研究者
- Core problem: 机会验真、估值联动和数据来源分散在多条输出中，导致同一标的的机会、风险、估值难以在一个包里解释清楚。

## Non-goals

- 不直接生成交易指令或自动下单。
- 不把样本数据或无法追溯来源的数据当成生产口径。
- 不承诺所有估值源都实时可用；上游缺失时允许降级展示。

## Constraints

- 主链路以真实数据为先，允许在数据源失败时降级到可解释的替代口径。
- 机会包需要兼容三市场输出节奏，并尽量复用现有 `run_real_pack_3markets.sh` 产物。
- DCF、外部估值、机会验真、来源映射都必须保留字段级可追踪性。

## Open Questions

- 统一机会包中，机会验真与估值联动块的最终排序与展示层级是否固定为“机会 -> 估值 -> 风险 -> 来源”。
- 字段级来源映射与可信度评分应展示在正文、附录，还是单独 JSON/表格。

## Requirements

### REQ-0001 维护击球区 M2 机会验真 latest 报表，输出 o

- Priority: P1
- Status: superseded
- Last updated: 2026-03-13T10:08:13.984072+08:00
- Linked KPIs: RESULT-TRACEABILITY
- Linked Tasks: None
- Source changes: CHG-0001
- Superseded by: CHG-0003, REQ-0003
- Body: 需要维护击球区 M2 机会验真 latest 报表，输出 open/closed/expired、方法组超额收益和命中率。
- Acceptance:
  - 实现并验证：维护击球区 M2 机会验真 latest 报表，输出 o
  - 结果回写到任务系统与 KPI 快照。

### REQ-0002 同一机会包展示机会验真结果与 DCF 估值联动

- Priority: P1
- Status: active
- Last updated: 2026-03-13T14:54:43.929393+08:00
- Linked KPIs: 关键结论可解释, 内容与数据覆盖, 产出节奏
- Linked Tasks: TASK-0004, TASK-0005, TASK-0006
- Source changes: CHG-0002
- Body: 在同一份机会包中同时展示机会验真结果与 DCF/外部估值关键字段，让单个标的的机会、风险、估值能一起解释。
- Acceptance:
  - 机会包正文至少同时包含机会验真结果、估值来源/区间、关键风险提示。
  - 当 DCF 不可用时，允许降级到 external valuation 或 close，但必须明确标注来源。
  - 统一输出优先复用 `docs/top20_opportunity_pack_real_3markets.md`、`output/opportunity_validation_latest.json` 等现有产物。

### REQ-0003 机会包补齐字段级来源映射与可信度评分

- Priority: P1
- Status: active
- Last updated: 2026-03-13T14:54:43.929393+08:00
- Linked KPIs: 关键结论可解释, 内容与数据覆盖
- Linked Tasks: TASK-0007, TASK-0008, TASK-0009
- Source changes: CHG-0003
- Body: 机会验真报表除命中率外，还必须输出字段级来源映射与可信度评分，保证用户能判断每个关键结论来自哪里、可信到什么程度。
- Acceptance:
  - 关键字段至少覆盖：机会状态、命中率/超额收益、估值来源、核心结论。
  - 每个关键字段都能标注来源系统或回退链路。
  - 可信度评分口径固定，缺失来源时不能伪造高可信分。

### REQ-0004 人工复核结果回写到 backlog、机会包和 KPI

- Priority: P1
- Status: active
- Last updated: 2026-03-14T22:38:51.934621+08:00
- Linked KPIs: FLOW-WRITEBACK-COMPLETION, RESULT-TRACEABILITY, BIZ-CUSTOM
- Linked Tasks: TASK-0010, TASK-0011, TASK-0012
- Source changes: CHG-0004, CHG-0006
- Body: 需要把人工复核结果回写到 backlog、机会包和 KPI，并保持本地工件与人工复核证据可追踪。

补充（CHG-0006）：新增并上调核心数据覆盖度为击球区最重要的KPI之一，需要按focus_pool、signal_pool、top50和整体池分层统计覆盖率，需要系统梳理所有API的能力边界、可查范围、免费层限制、频率预算，需要建立每日固定运行的API增量抓取机制，把能合法获取且未入库的数据持续写入本地数据库，核心数据定义为系统实际需要用到的行情、财务、估值校验、宏观与披露数据，并固化成后续日常数据沉淀规则，已经存在且未变化的数据不要重复存储，逐步形成完整数据库
- Acceptance:
  - 人工复核结果回写后，backlog 或关联工件能够看到对应 review status 与证据引用。
  - 机会包消费人工复核结果后，关键结论或复核状态在正文或附属工件中可见。
  - KPI 快照消费人工复核结果后，相关指标保留 evidence refs 并能追溯到 review 工件。
  - 外部查看面失败时，不阻断本地 writeback 与证据落盘。
  - 补充要求来自 CHG-0006。
