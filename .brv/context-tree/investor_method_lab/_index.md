---
children_hash: 955ca94595edb586e8cdc14186481d249a7cef3d7e5cb2bc082f52a96d57db41
compression_ratio: 0.281888182122531
condensation_order: 2
covers: [context.md, methodologies/_index.md, overview/_index.md, requirements/_index.md, technical/_index.md, workflow/_index.md]
covers_token_total: 2987
summary_level: d2
token_count: 842
type: summary
---
# Investor Method Lab: Level d2 Structural Summary

The **investor_method_lab** is a systematic framework designed to identify top-tier investors, extract their methodologies, and perform automated opportunity screening. It emphasizes traceability, high-fidelity data integration, and a reviewable "Opportunity Pack" output for decision support.

## 1. Project Foundation and Architecture
The project is structured into three layers: **Data** (investor profiles/methodologies), **Scripts** (automation/ranking), and **Docs** (templates/playbooks). It operates on a core workflow of `Investor Identification` → `Methodology Extraction` → `Opportunity Screening` → `Opportunity Pack Generation`.

*   **Key Constraints**: No trading execution; no untraceable sample data in production; explicit labeling for degraded valuation sources.
*   **Technical Stack**: Centralized via `stock-data-hub` (`IML_STOCK_DATA_HUB_URL`), with a web dashboard at `http://127.0.0.1:8090/web/`.
*   **Reference**: `overview/_index.md`, `context.md`.

## 2. Core Systems and Technical Implementation
Technical operations focus on data routing, valuation integrity, and manual review integration.

*   **Valuation Coverage System**: Manages a 0-4 priority scale for stock valuations, prioritizing "Formal Support" (tiers 3-4) and falling back to `targetMeanPrice` or `close` prices.
*   **Review Writeback System**: Normalizes manual review decisions (e.g., promote, watch, archive) into a system-actionable backlog using `RWB-` prefixes and ticker-based deduplication.
*   **Data Routing & Caching**: Uses `Futu OpenD` for A/HK markets with `Yahoo Finance` as a fallback. Implements a 24-hour cache at `data/cache/yfinance`.
*   **Orchestration**: Primary execution is handled via `scripts/run_real_pack_3markets.sh` and the `PAI Loop` (`scripts/pai_loop.py`).
*   **Reference**: `technical/_index.md`.

## 3. Methodologies and Evaluation Framework
Investment strategies are governed by quantitative thresholds and structured scoring.

*   **Evaluation Metrics**:
    *   **Margin of Safety (MOS)**: `1 - (price / fair_value)`.
    *   **Certainty Score**: Reliability metric for valuations.
*   **Value Quality Compound Strategy**: Requires `MOS >= 15%` and `Certainty Score >= 65`. Penalties apply if MOS drops below 30% or Certainty below 75.
*   **Reference**: `methodologies/_index.md`.

## 4. Requirement Operations and Traceability
Requirements (REQs) are managed as JSON-authoritative blocks to ensure field-level traceability from market data to final opportunity status.

*   **REQ-0002 (Valuation Linkage)**: Integrates DCF and external valuations into a single pack to explain risks and targets holistically.
*   **REQ-0003 (Source Traceability)**: Mandates standardized credibility scores and field-level mapping, superseding earlier validation reports.
*   **Reference**: `requirements/_index.md`.

## 5. Standard Workflows and Execution
Operational maintenance follows defined temporal cadences managed via the PAI Loop.

*   **Maintenance Cycles**: Weekly (Investors/Performance), Bi-weekly (Methodologies/Factor Weights), and Daily (Opportunities/Candidate Pools).
*   **Automation**: Scheduled via `PAI_REAL_CRON` (default 09:10). Successful runs trigger automated notifications for **DCF Calibration** and **Opportunity Mining**.
*   **Reference**: `workflow/_index.md`.