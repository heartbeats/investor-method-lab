---
title: Project Overview
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-13T02:25:00.288Z'
updatedAt: '2026-03-13T02:25:00.288Z'
---
## Raw Concept
**Task:**
Systematically find top investors, extract methodologies, and discover opportunities.

**Flow:**
Investor identification -> Methodology extraction -> Opportunity screening -> Opportunity pack generation

**Timestamp:** 2026-03-13

**Author:** Lucas

## Narrative
### Structure
The project is organized into data (investors, methodologies), scripts (ranking, building profiles), and docs (templates, playbooks).

### Highlights
Provides a unified opportunity package linking validation with DCF/external valuations.

### Rules
Rule 1: No trading execution
Rule 2: No untraceable sample data in production
Rule 3: Explicit labeling for degraded valuation sources

## Facts
- **investor-method-lab**: The investor-method-lab project aims to create a reviewable and traceable opportunity package that unifies opportunity validation with DCF or external valuation.
- **investor-method-lab**: Primary users of the project are Lucas and daily research users.
- **investor-method-lab**: Non-goals for the project include trading execution, production use of untraceable sample data, and pretending all valuation sources are real-time.
- **investor-method-lab**: The project can integrate with 'stock-data-hub' via the environment variable 'IML_STOCK_DATA_HUB_URL=http://127.0.0.1:18123'.
- **investor-method-lab**: The investor-method-lab project aims to produce reviewable and traceable real data opportunity packs that link validation results with DCF or external valuations.
- **investor-method-lab**: The primary target users are Lucas, the main reviewer and decision support user, and investment researchers performing daily updates.
- **investor-method-lab**: The core problem the project addresses is the dispersion of opportunity validation, valuation linkage, and data sources across multiple outputs.
- **investor-method-lab**: Table data must be processed row by row and must not be summarized.
- **investor-method-lab**: Exact code examples, API signatures, and interface definitions must be preserved.
- **investor-method-lab**: The project documentation includes a component or file named narrative.rules.
- **investor-method-lab**: Step-by-step procedures and numbered instructions within narrative.rules must be preserved.
