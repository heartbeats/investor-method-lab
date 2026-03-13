---
title: Project Requirements
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-13T02:44:46.567Z'
updatedAt: '2026-03-13T02:44:46.567Z'
---
## Raw Concept
**Task:**
Define and track investor-method-lab requirements

**Changes:**
- Added REQ-0002 for valuation linkage
- Added REQ-0003 for source traceability

**Files:**
- .ai/requirement_ops/requirements.md
- .ai/requirement_ops/effective_requirements.md

**Flow:**
requirements.md (canonical) -> effective_requirements.md (execution view)

**Timestamp:** 2026-03-13

## Narrative
### Structure
Requirements are managed via a JSON-authoritative block in requirements.md, with an effective view for execution.

### Highlights
Goal: Stable output of reviewable, traceable opportunity packs with DCF/external valuation linkage.

### Rules
Rule 1: Real data first, allow fallback to explainable alternatives.
Rule 2: Maintain field-level traceability for DCF and opportunity validation.
Rule 3: Do not generate automated trading orders.

### Examples
REQ-0002: Link opportunity validation with DCF in one pack.
REQ-0003: Add field-level source mapping and confidence scores.

## Facts
- **investor-method-lab**: The project goal is to stably produce reviewable and traceable real data opportunity packs linked with DCF/external valuations to support daily research.
- **investor-method-lab**: Target users include Lucas (main reviewer/decision support user) and investment researchers conducting daily research on opportunity packs.
- **investor-method-lab**: The core problem is that opportunity validation, valuation linkage, and data sources are scattered, making it difficult to explain a single target's opportunities, risks, and valuations together.
- **investor-method-lab**: The project will not directly generate trading orders or automatic orders.
- **investor-method-lab**: Sample data or untraceable data will not be used as production standards.
- **investor-method-lab**: The project does not guarantee real-time availability of all valuation sources and allows for degraded display when upstream data is missing.
- **investor-method-lab**: The main path prioritizes real data but allows degradation to explainable alternatives if data sources fail.
- **investor-method-lab**: Opportunity packs must be compatible with three-market output rhythms and should reuse existing run_real_pack_3markets.sh products.
- **investor-method-lab**: Field-level traceability must be maintained for DCF, external valuations, opportunity validation, and source mapping.
- **REQ-0001**: REQ-0001 requires maintaining the M2 opportunity validation latest report, outputting open/closed/expired status, group excess returns, and hit rates.
- **REQ-0001**: REQ-0001 has been superseded by REQ-0003 and CHG-0003.
- **REQ-0002**: REQ-0002 requires displaying opportunity validation results and DCF/external valuation linkage in the same pack to explain a target's opportunities, risks, and valuations together.
- **REQ-0002**: REQ-0002 is currently active and linked to tasks TASK-0004, TASK-0005, and TASK-0006.
- **REQ-0003**: REQ-0003 requires the opportunity pack to include field-level source mapping and credibility scores to ensure users can judge the origin and reliability of key conclusions.
- **REQ-0003**: REQ-0003 is currently active and linked to tasks TASK-0007, TASK-0008, and TASK-0009.
- **机会验真报表**: 机会验真报表除命中率外，还必须输出字段级来源映射与可信度评分
- **用户透明度**: 保证用户能判断每个关键结论来自哪里、可信到什么程度
- **关键字段**: 关键字段至少覆盖：机会状态、命中率/超额收益、估值来源、核心结论
- **字段来源标注**: 每个关键字段都能标注来源系统或回退链路
- **可信度评分**: 可信度评分口径固定
- **可信度评分**: 缺失来源时不能伪造高可信分
- **table data processing**: Do not summarize table data with every row.
- **code and API definitions**: Preserve exact code examples, API signatures, and interface definitions.
- **procedural instructions**: Preserve step-by-step procedures and numbered instructions in narrative.rules.
