---
children_hash: c600cfafb7a77d68568aae382ad35088052f12cbb723caefff2dd5310b767571
compression_ratio: 0.7595419847328244
condensation_order: 1
covers: [context.md, technical_implementation.md]
covers_token_total: 524
summary_level: d1
token_count: 398
type: summary
---
# Technical Implementation Overview

Structural summary of the project's integration logic, data routing, and script architecture.

### Core Architecture & Orchestration
- **Main Orchestrator**: `scripts/run_real_pack_3markets.sh` is the primary execution script for the 3-market pack.
- **Iteration Loop**: `scripts/pai_loop.py` manages the PAI iteration cycle.
- **Web Interface**: Local dashboard accessible at `http://127.0.0.1:8090/web/` (Entry: `web/index.html`, `web/investor.html`).

### Data Strategy & Routing
- **Valuation Priority**: `dcf_iv_base` > `targetMeanPrice` > `close`.
- **Source Fallback**: `build_investor_profiles.py` routes A/HK market data via **Futu OpenD**, falling back to **Yahoo Finance**.
- **Caching**: 24-hour cache at `data/cache/yfinance`; `build_real_opportunities.py` supports a `--no-cache` flag.
- **Manual Calibration**: `data/dcf_special_focus_list.json` tracks manual DCF overrides.

### Key Knowledge Components
- **Investor & Methodology Data**:
    - `data/investors.json`: Central investor database.
    - `data/methodologies.json`: Classification and screening rulebook.
- **Analysis Scripts**:
    - `scripts/rank_investors.py`: Ranking logic.
    - `scripts/rank_opportunities.py`: Strategy-based output generation.
    - `scripts/build_real_opportunities.py`: Opportunity data construction.
- **Dependencies**: Futu OpenD, Yahoo Finance, `stock-data-hub`, `dcf-valuation-link`.

*Refer to [technical_implementation.md](technical_implementation.md) for full script signatures and [context.md](context.md) for high-level integration details.*