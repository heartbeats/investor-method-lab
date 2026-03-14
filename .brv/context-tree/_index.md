---
children_hash: 31ab07222f9e33331d056802474f09e43a9d6d86cbcbd70948c7640cf3e2a2b1
compression_ratio: 0.8795698924731182
condensation_order: 3
covers: [investor_method_lab/_index.md]
covers_token_total: 930
summary_level: d3
token_count: 818
type: summary
---
# Investor Method Lab: Level d3 Structural Summary

The **investor_method_lab** is a systematic framework for investor identification, methodology extraction, and automated opportunity screening. It is built on a foundation of traceability, high-fidelity data integration, and reviewable decision support via "Opportunity Packs."

## 1. Architectural Framework and Core Workflow
The system operates across three functional layers—**Data** (profiles/methodologies), **Scripts** (automation/ranking), and **Docs** (playbooks/templates)—to execute a standardized pipeline: `Identification` → `Extraction` → `Screening` → `Pack Generation`.

*   **System Constraints**: Prohibits trading execution and untraceable production data; mandates explicit labeling for degraded valuation sources.
*   **Centralized Infrastructure**: Anchored by `stock-data-hub` (`IML_STOCK_DATA_HUB_URL`) and a web dashboard (`http://127.0.0.1:8090/web/`).
*   **Reference**: `investor_method_lab/overview/_index.md`, `investor_method_lab/context.md`.

## 2. Technical Systems and Data Orchestration
Technical implementation focuses on valuation integrity, data routing, and manual-to-system feedback loops.

*   **Valuation & Pricing**: Implements a 0-4 priority scale for stock valuations (Tiers 3-4 preferred). Data is routed through `Futu OpenD` for A/HK markets with `Yahoo Finance` fallbacks and a 24-hour cache at `data/cache/yfinance`.
*   **Review Writeback (RWB)**: Normalizes manual review actions (promote, watch, archive) into a system-actionable backlog using `RWB-` prefixes and ticker-based deduplication.
*   **Execution Orchestration**: Managed via `scripts/run_real_pack_3markets.sh` and the `PAI Loop` (`scripts/pai_loop.py`).
*   **Reference**: `investor_method_lab/technical/_index.md`.

## 3. Investment Methodologies and Scoring
Strategies are governed by quantitative thresholds and structured reliability metrics.

*   **Key Metrics**: Uses **Margin of Safety (MOS)** (`1 - price/fair_value`) and **Certainty Score** (valuation reliability).
*   **Value Quality Compound Strategy**: Enforces a minimum `MOS >= 15%` and `Certainty Score >= 65`, with penalties if MOS falls below 30% or Certainty below 75.
*   **Reference**: `investor_method_lab/methodologies/_index.md`.

## 4. Requirement Operations and Traceability
Requirements (REQs) are managed as JSON-authoritative blocks to ensure end-to-end field-level traceability.

*   **REQ-0002 (Valuation Linkage)**: Integrates DCF and external valuations into unified packs to explain risks and targets.
*   **REQ-0003 (Source Traceability)**: Mandates standardized credibility scores and field-level mapping, superseding legacy validation reports.
*   **Reference**: `investor_method_lab/requirements/_index.md`.

## 5. Operational Workflows and Maintenance
Maintenance is structured into temporal cadences managed via the PAI Loop and scheduled automation.

*   **Cycles**: Weekly (Investors/Performance), Bi-weekly (Methodologies/Factor Weights), and Daily (Opportunities/Candidate Pools).
*   **Automation**: Scheduled via `PAI_REAL_CRON` (09:10 default). Successful execution triggers automated **DCF Calibration** and **Opportunity Mining** notifications.
*   **Reference**: `investor_method_lab/workflow/_index.md`.