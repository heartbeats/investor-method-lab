---
children_hash: 6c82df0578409e96c2e733251b482f0bf64289ee5c44cc455fe3ec77cff97be9
compression_ratio: 0.6530612244897959
condensation_order: 1
covers: [context.md, standard_workflows.md]
covers_token_total: 392
summary_level: d1
token_count: 256
type: summary
---
# Domain: workflow

## Overview
Execution and maintenance procedures centered on the PAI Loop and iterative cycles for investors, methodologies, and opportunities.

## Standard Workflows
Defined maintenance and execution cycles managed through specific temporal cadences:
- **Weekly (Investors):** Update profiles, performance metrics (Max Drawdown), and public material completeness.
- **Bi-weekly (Methodologies):** Review strategies, merge categories, and update factor weights.
- **Daily (Opportunities):** Update candidate pools and execute screening to generate observation top lists.

## Technical Execution & Notifications
- **Cron Strategy:** 'Real' mode defaults to `09:10` daily; configurable via `PAI_REAL_CRON`.
- **Automated Outputs:** Successful 'real' mode execution triggers two distinct notification modules:
    - `【特别关注｜深度DCF校准】` (DCF Calibration)
    - `【机会挖掘｜新增候选】` (Opportunity Mining)

*Refer to [standard_workflows.md](standard_workflows.md) for detailed rule sets and environment configurations.*