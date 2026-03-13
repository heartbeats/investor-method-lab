---
children_hash: 0b5046969cc36cf9ab7307e885e22efe2f71da71c526ee573f31570f6d6d87f8
compression_ratio: 0.9921568627450981
condensation_order: 3
covers: [investor_method_lab/_index.md]
covers_token_total: 1020
summary_level: d3
token_count: 1012
type: summary
---
# Investor Method Lab: Structural Summary (Level d3)

This level d3 summary provides a high-level structural overview of the **investor-method-lab**, synthesizing core strategic objectives, technical infrastructure, and operational governance into a unified framework for systematic investment analysis.

## 1. Strategic Framework and Core Objectives
The project functions as a systematic environment for extracting investor methodologies and generating traceable investment signals. The primary goal is the production of **Opportunity Packs**, which merge market data with intrinsic valuations to support stakeholder research.

*   **Strategic Output**: Generation of **Opportunity Packs** that integrate automated screening results with holistic risk/valuation data.
*   **Methodology Standards**: Strategies (e.g., **Value Quality Compound**) are governed by strict quantitative thresholds, specifically `MOS >= 15%` and `Certainty Score >= 65`.
*   **Drill-down**: See `investor_method_lab/overview/` and `investor_method_lab/methodologies/` for specific strategy definitions and scoring rules.

## 2. Technical Architecture and Data Orchestration
The system utilizes a three-layer architecture (Data, Scripts, Docs) designed for high-integrity data routing and integration with external valuation providers.

*   **Execution & Orchestration**: Primary workflows are driven by `scripts/run_real_pack_3markets.sh` for multi-market processing and `scripts/pai_loop.py` for iterative analysis.
*   **Data Routing & Priority**: Implements a strict valuation fallback hierarchy: `dcf_iv_base` > `targetMeanPrice` > `close`.
*   **External Integration**: Interfaces with `stock-data-hub` via `IML_STOCK_DATA_HUB_URL`. Market data for A/HK markets is sourced via **Futu OpenD**, with **Yahoo Finance** serving as the primary fallback and 24-hour cache provider (`data/cache/yfinance`).
*   **Drill-down**: See `investor_method_lab/technical/` for API signatures and detailed integration logic.

## 3. Governance, Requirements, and Traceability
Operational integrity is maintained through a centralized "Source of Truth" management system and strict traceability requirements.

*   **Requirement Management**: Canonical requirements are localized in `.ai/requirement_ops/requirements.md`, with execution-ready views in `effective_requirements.md`.
*   **Traceability Standards (REQ-0003)**: Mandates field-level source mapping and credibility scoring for all analytical conclusions.
*   **Valuation Linkage (REQ-0002)**: Requires the unified integration of DCF metrics and opportunity status within all generated reports.
*   **Drill-down**: See `investor_method_lab/requirements/` for REQ, Task, and KPI lifecycle management.

## 4. Operational Workflows and System Constraints
System behavior is governed by fixed temporal cadences and non-negotiable operational boundaries.

*   **Operational Cadence**:
    *   **Daily**: Opportunity screening and candidate pool updates (Real mode execution at `09:10`).
    *   **Weekly/Bi-weekly**: Updates to investor profiles and methodology strategy/factor weight reviews.
*   **Non-Negotiable Constraints**:
    *   **Rule 1**: Prohibition of automated trading execution.
    *   **Rule 2**: Exclusion of untraceable sample data from production environments.
    *   **Rule 3**: Mandatory labeling for any degraded or fallback valuation sources.
*   **Drill-down**: See `investor_method_lab/workflow/` for PAI Loop maintenance and notification triggers.

## 5. Knowledge Domain Map
| Domain | Focus Area | Primary Reference |
| :--- | :--- | :--- |
| **Methodologies** | Strategy frameworks, MOS, and Certainty scoring. | `methodologies/context.md` |
| **Overview** | Foundations, architectural layers, and goals. | `overview/context.md` |
| **Requirements** | Lifecycle of REQs, Tasks, and KPIs. | `requirements/context.md` |
| **Technical** | Integration logic, script signatures, and routing. | `technical/context.md` |
| **Workflow** | PAI Loop maintenance and temporal cadences. | `workflow/context.md` |