---
title: Review Writeback System
tags: []
keywords: []
importance: 50
recency: 1
maturity: draft
createdAt: '2026-03-14T01:45:15.799Z'
updatedAt: '2026-03-14T01:45:15.799Z'
---
## Raw Concept
**Task:**
Implementation of Review Writeback System

**Changes:**
- Implemented sync receipt support
- Added failure fallbacks for stable artifacts
- Implemented JSON error tolerance in loaders

**Files:**
- src/investor_method_lab/review_writeback.py
- tests/test_review_writeback.py

**Flow:**
load review -> normalize payload -> deduplicate by ticker -> generate backlog -> build payload

**Timestamp:** 2026-03-14

## Narrative
### Structure
Located in src/investor_method_lab/review_writeback.py. Handles normalization and processing of manual review decisions.

### Dependencies
Depends on JSON loaders and external sync receipts (e.g., Feishu).

### Highlights
Supports manual decision actions like promote_to_pack, keep_in_watch_pool, archive, and upgrade_valuation_source. Provides automatic backlog generation with priority sorting.

### Rules
Rule 1: load_review_writeback must handle broken JSON by returning count 0 and error reason.
Rule 2: reviewed_items_by_ticker keeps only the latest review per ticker based on manual_reviewed_at.

### Examples
Manual Decision Mapping: 通过 -> promote_to_pack, 观察 -> keep_in_watch_pool, 驳回 -> archive, 升级 -> upgrade_valuation_source.

## Facts
- **review_action_mapping**: Manual action '通过' maps to 'promote_to_pack' [convention]
- **review_action_mapping**: Manual action '观察' maps to 'keep_in_watch_pool' [convention]
- **review_action_mapping**: Manual action '驳回' maps to 'archive' [convention]
- **review_action_mapping**: Manual action '升级' maps to 'upgrade_valuation_source' [convention]
- **backlog_id_format**: Backlog items are assigned IDs with prefix 'RWB-' [project]
