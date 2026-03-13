---
title: Standard Workflows
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-13T02:25:00.295Z'
updatedAt: '2026-03-13T02:25:00.295Z'
---
## Raw Concept
**Task:**
Define project maintenance and execution cycles.

**Flow:**
Weekly (Investors) -> Bi-weekly (Methodologies) -> Daily (Opportunities)

**Timestamp:** 2026-03-13

## Narrative
### Structure
Maintenance cycles for investors, methodologies, and daily opportunity screening.

### Highlights
Includes automated PAI loop for continuous iteration.

### Rules
1. Update investor profiles weekly.
2. Review methodologies bi-weekly.
3. Update candidate pool daily.

## Facts
- **Standard Workflow**: The weekly workflow involves updating investor profiles, including performance, maximum drawdown, and public material completeness.
- **Standard Workflow**: The bi-weekly workflow involves reviewing methodologies, adding or merging strategy categories, and updating factor weights.
- **Standard Workflow**: The daily workflow includes updating the candidate pool and running opportunity screening to generate top lists for the observation pool.
- **Cron Strategy**: The default cron strategy for the 'real' mode is set to 09:10 daily, which can be overridden by the PAI_REAL_CRON environment variable.
- **Notifications**: Successful 'real' mode pushes are split into two messages: '【特别关注｜深度DCF校准】' and '【机会挖掘｜新增候选】'.
