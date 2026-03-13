---
title: Technical Implementation
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-13T02:25:00.296Z'
updatedAt: '2026-03-13T02:25:00.296Z'
---
## Raw Concept
**Task:**
Technical details of scripts, data sources, and integrations.

**Files:**
- scripts/build_real_opportunities.py
- scripts/build_investor_profiles.py
- scripts/pai_loop.py

**Timestamp:** 2026-03-13

## Narrative
### Structure
Scripts for data fetching, profile building, and the PAI iteration loop.

### Dependencies
Futu OpenD, Yahoo Finance, stock-data-hub, dcf-valuation-link.

### Highlights
Support for 24-hour caching and multi-source fallback.

### Rules
Valuation Priority: dcf_iv_base > targetMeanPrice > close

## Facts
- **Project Structure**: The project data directory includes 'data/investors.json' for the investor database and 'data/methodologies.json' for classification and screening rules.
- **Project Structure**: The 'scripts/' directory contains 'rank_investors.py' for ranking analysis and 'rank_opportunities.py' for strategy-based output.
- **Project Structure**: The project includes a web dashboard accessible at 'http://127.0.0.1:8090/web/' with entry points like 'web/index.html' and 'web/investor.html'.
- **build_real_opportunities.py**: The script 'build_real_opportunities.py' defaults to a 24-hour cache located at 'data/cache/yfinance' and supports a '--no-cache' flag for real-time data.
- **DCF Integration**: Valuation priority is set as 'dcf_iv_base > targetMeanPrice > close'.
- **build_investor_profiles.py**: The script 'build_investor_profiles.py' routes A/HK market data through 'Futu OpenD' then 'Yahoo Finance'.
- **Project Structure**: A special focus list for manual DCF calibration is maintained in 'data/dcf_special_focus_list.json'.
- **scripts/run_real_pack_3markets.sh**: The script scripts/run_real_pack_3markets.sh is the current main orchestration script for the 3-market real pack.
