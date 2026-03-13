---
title: Investment Methodologies
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-13T02:25:00.298Z'
updatedAt: '2026-03-13T02:25:00.298Z'
---
## Raw Concept
**Task:**
Define and execute investment strategies.

**Timestamp:** 2026-03-13

## Narrative
### Structure
Methodologies are classified into strategies like Value Quality Compound.

### Highlights
Specific thresholds for Margin of Safety and Certainty Score.

### Rules
Value Quality Compound: MOS >= 15%, Certainty >= 65.

## Facts
- **value_quality_compound**: The 'Value Quality Compound' strategy requires a hard threshold of margin_of_safety >= 15% and a certainty_score >= 65 if available.
- **value_quality_compound**: A soft penalty is applied to the 'Value Quality Compound' strategy score if margin_of_safety is less than 30% or certainty_score is less than 75.
- **Acceptance Criteria**: The Margin of Safety (MOS) is calculated using the formula: margin_of_safety = 1 - (price / fair_value).
