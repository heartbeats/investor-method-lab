---
children_hash: 24bbb8ad438917ec3d90be85779b8f4c690e6ce16164966ab6d9a9ec00b87ee9
compression_ratio: 0.36250486192143133
condensation_order: 2
covers: [context.md, methodologies/_index.md, overview/_index.md, requirements/_index.md, technical/_index.md, workflow/_index.md]
covers_token_total: 2571
summary_level: d2
token_count: 932
type: summary
---
# Investor Method Lab: Structural Summary (Level d2)

This summary integrates the foundational objectives, technical architecture, and operational frameworks of the **investor-method-lab** project, a systematic environment for investor analysis and opportunity discovery.

## 1. Core Objectives and Strategic Framework
The project aims to identify top-tier investors, extract their methodologies, and perform automated screening to generate traceable **Opportunity Packs**. These packs link market data with DCF (Discounted Cash Flow) and external valuations to support daily research for key stakeholders.

*   **Primary Output**: Opportunity Packs integrating validation results with holistic risk/valuation data.
*   **Methodology Standards**: Strategies like **Value Quality Compound** utilize hard thresholds (e.g., `MOS >= 15%`, `Certainty Score >= 65`) to identify high-quality investments.
*   **Key References**: `overview/_index.md`, `methodologies/_index.md`.

## 2. Technical Architecture and Data Routing
The system is built on a three-layer structure (Data, Scripts, Docs) with standardized integration logic for external valuation systems.

*   **Orchestration**: Core execution is handled by `scripts/run_real_pack_3markets.sh` (3-market pack) and `scripts/pai_loop.py` (PAI iteration).
*   **Data Strategy**: Implements a valuation priority of `dcf_iv_base` > `targetMeanPrice` > `close`.
*   **External Integration**: Connects to `stock-data-hub` via `IML_STOCK_DATA_HUB_URL`. Data routing for A/HK markets uses **Futu OpenD** with **Yahoo Finance** as a fallback.
*   **Caching**: 24-hour cache maintained at `data/cache/yfinance`.
*   **Key References**: `technical/_index.md`, `overview/_index.md`.

## 3. Requirements and Traceability Management
The project enforces strict "Source of Truth" management to ensure data integrity and transparency.

*   **Management**: Canonical requirements are stored in `.ai/requirement_ops/requirements.md`, with execution views in `effective_requirements.md`.
*   **Traceability (REQ-0003)**: Mandates field-level source mapping and credibility scores for all conclusions.
*   **Valuation Linkage (REQ-0002)**: Holistic integration of DCF and opportunity status within a single report.
*   **Key References**: `requirements/_index.md`.

## 4. Operational Workflows and Constraints
Execution is governed by defined temporal cadences and strict non-negotiable rules.

*   **Cadence**: 
    *   **Daily**: Opportunity screening and candidate pool updates (Real mode defaults to `09:10`).
    *   **Weekly**: Investor profile and performance updates.
    *   **Bi-weekly**: Methodology strategy reviews and factor weight adjustments.
*   **Constraints**: 
    *   **Rule 1**: No automated trading execution.
    *   **Rule 2**: No untraceable sample data in production.
    *   **Rule 3**: Mandatory labels for degraded valuation sources.
*   **Automated Notifications**: Triggers specific modules for `DCF Calibration` and `Opportunity Mining` upon successful execution.
*   **Key References**: `workflow/_index.md`, `overview/_index.md`.

## 5. Domain Directory
| Domain | Focus | Key Files |
| :--- | :--- | :--- |
| **Methodologies** | Strategy frameworks and MOS/Certainty scoring rules. | `methodologies/investment_methodologies.md` |
| **Overview** | Foundations, architectural layers, and primary goals. | `overview/project_overview.md` |
| **Requirements** | Lifecycle management of REQs, Tasks, and KPIs. | `requirements/requirement_ops.md` |
| **Technical** | Integration logic, script signatures, and data routing. | `technical/technical_implementation.md` |
| **Workflow** | PAI Loop maintenance and notification cadences. | `workflow/standard_workflows.md` |