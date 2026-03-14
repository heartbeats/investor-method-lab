---
children_hash: 94b4c4e6bcb7b1832ec500cb116065105e535675bcfdbd9a1ee5ff503c195610
compression_ratio: 0.5682788051209103
condensation_order: 1
covers: [context.md, review_writeback_system.md, technical_implementation.md, valuation_coverage_system.md]
covers_token_total: 1406
summary_level: d1
token_count: 799
type: summary
---
# Technical Domain Structural Summary

This domain covers the core data routing, integration logic, and valuation systems governing the investor methodology laboratory.

## Core Systems & Architectures

### Review Writeback System
**Entry:** `review_writeback_system.md`
*   **Purpose:** Normalizes and processes manual review decisions into actionable backlogs.
*   **Key Files:** `src/investor_method_lab/review_writeback.py`, `tests/test_review_writeback.py`
*   **Logic Flow:** `load review -> normalize payload -> deduplicate by ticker -> generate backlog -> build payload`.
*   **Key Decisions:**
    *   **Deduplication:** Keeps only the latest review per ticker based on `manual_reviewed_at`.
    *   **Error Handling:** Loaders return count 0 and error reasons for broken JSON instead of failing.
    *   **Decision Mappings:** Maps manual inputs to system actions: '通过' (promote_to_pack), '观察' (keep_in_watch_pool), '驳回' (archive), and '升级' (upgrade_valuation_source).
    *   **ID Convention:** Backlog items use the prefix `RWB-`.

### Valuation Coverage System
**Entry:** `valuation_coverage_system.md`
*   **Purpose:** Manages coverage analysis, historical trend tracking, and gap identification for stock valuations.
*   **Key Files:** `src/investor_method_lab/valuation_coverage.py`, `tests/test_valuation_coverage.py`
*   **Logic Flow:** `analyze coverage -> derive support tiers -> identify gaps -> record snapshot -> render markdown`.
*   **Quality Tiers:** Establishes a 0-4 priority scale:
    *   **4 (formal_core)** / **3 (formal_support)**: Defined as "Formal Support."
    *   **2 (unknown)** / **1 (reference_only)** / **0 (price_fallback)**.
*   **Architectural Decisions:** `append_history` prevents duplicates if metrics match the last entry date. Gap analysis specifically targets tickers lacking tiers 3 or 4.

### Technical Implementation & Integration
**Entry:** `technical_implementation.md`, `context.md`
*   **Data Routing:** `build_investor_profiles.py` routes A/HK market data through Futu OpenD, falling back to Yahoo Finance.
*   **Valuation Priority:** `dcf_iv_base > targetMeanPrice > close`.
*   **Caching Strategy:** `build_real_opportunities.py` defaults to a 24-hour cache at `data/cache/yfinance` (bypassable via `--no-cache`).
*   **Orchestration:** `scripts/run_real_pack_3markets.sh` serves as the primary execution script for the 3-market real pack.
*   **Key Components:**
    *   **Data Hub:** Centralized data source routing and caching.
    *   **PAI Loop:** Iteration loop managed via `scripts/pai_loop.py`.
    *   **Web Dashboard:** Accessible at `http://127.0.0.1:8090/web/` for visualizing results.

## Key Relationships & Dependencies
*   **External Integrations:** Futu OpenD, Yahoo Finance, and sync receipts (Feishu).
*   **Data Dependencies:** The systems rely on `stock-data-hub` and `dcf-valuation-link`.
*   **Repository Structure:**
    *   `data/investors.json`: Investor database.
    *   `data/methodologies.json`: Screening and classification rules.
    *   `data/dcf_special_focus_list.json`: Manual DCF calibration targets.
    *   `scripts/`: Contains core analysis scripts (`rank_investors.py`, `rank_opportunities.py`).