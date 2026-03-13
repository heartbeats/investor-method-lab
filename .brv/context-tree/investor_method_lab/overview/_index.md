---
children_hash: ecedc2a744235dc5e8e9272fb54e76e734ebe8fef7e6503df9a3d0046973542d
compression_ratio: 0.96
condensation_order: 1
covers: [context.md, project_overview.md]
covers_token_total: 650
summary_level: d1
token_count: 624
type: summary
---
# Domain Summary: investor_method_lab/overview

The **overview** domain establishes the foundational goals, architectural constraints, and operational workflows for the **investor-method-lab** project. It defines a systematic framework for investor analysis and opportunity discovery, emphasizing traceability and integration with external valuation systems.

## Core Objectives and Scope
The primary task of the project is to systematically identify top investors, extract their investment methodologies, and perform automated opportunity screening. The ultimate output is a reviewable **Opportunity Pack** that links validation results with DCF (Discounted Cash Flow) or external valuations.

- **Primary Users:** Lucas (Main Reviewer/Decision Support) and daily investment researchers.
- **Non-Goals:** Trading execution, production use of untraceable sample data, and real-time valuation posturing.

## Architectural Structure and Flow
The project is organized into three primary layers as detailed in [project_overview.md]:
1.  **Data:** Centralized repositories for investor profiles and methodologies.
2.  **Scripts:** Automation for ranking and building investor profiles.
3.  **Docs:** Standardized templates and playbooks.

**Process Workflow:**
`Investor Identification` → `Methodology Extraction` → `Opportunity Screening` → `Opportunity Pack Generation`

## Technical Integration and Decisions
- **External Integration:** Connects to `stock-data-hub` via the environment variable `IML_STOCK_DATA_HUB_URL=http://127.0.0.1:18123`.
- **Data Integrity:** Explicit labeling is required for any degraded valuation sources to maintain transparency.
- **Key Concepts:** Focuses on Opportunity Pack generation, Methodology Extraction, and DCF Integration [context.md].

## Operational Rules and Constraints
The project adheres to strict processing and documentation standards defined in [project_overview.md]:
- **Rule 1:** No trading execution.
- **Rule 2:** No untraceable sample data in production.
- **Rule 3:** Explicit labeling for degraded valuation sources.
- **Data Processing:** Table data must be processed row-by-row without summarization to ensure precision.
- **Documentation:** Exact code examples, API signatures, and numbered procedures within `narrative.rules` must be preserved verbatim.

## Reference Entries
- **[context.md]**: High-level overview and list of key concepts.
- **[project_overview.md]**: Detailed project task definitions, flow, rules, and technical facts.