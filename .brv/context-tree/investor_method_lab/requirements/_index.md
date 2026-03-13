---
children_hash: 8eaba1e6a3072f4e1ba03de10f79988088ae269cca4be3a55a01aa4423540dc9
compression_ratio: 0.4210843373493976
condensation_order: 1
covers: [context.md, project_requirements.md, requirement_ops.md]
covers_token_total: 1660
summary_level: d1
token_count: 699
type: summary
---
# Domain: investor_method_lab
## Topic: Requirements (Level d1 Summary)

### Overview
The requirements domain manages the lifecycle of project goals, tasks, and implementation statuses for the investor-method-lab. The primary objective is to produce stable, reviewable, and traceable "opportunity packs" that link real-market data with DCF and external valuations to support daily investment research for users like Lucas and other researchers.

### Architectural Decisions & Management
*   **Source of Truth**: Requirements are managed via a JSON-authoritative block in `.ai/requirement_ops/requirements.md`.
*   **Execution View**: An effective view for execution is maintained in `.ai/requirement_ops/effective_requirements.md`.
*   **Requirement-to-Task Mapping**: Requirements (REQ) are directly linked to specific tasks (TASK) and KPIs to ensure implementation traceability.
*   **Data Strategy**: Prioritizes "real data first" but implements explicit degradation rules to external valuations or close prices when primary DCF data is unavailable.

### Key Requirements & Relationships
*   **REQ-0002: Valuation Linkage** (Active)
    *   **Focus**: Integration of opportunity validation results and DCF/external valuations into a single pack to explain target opportunities, risks, and valuations holistically.
    *   **Status**: Supplemented with specific acceptance criteria; linked to **TASK-0004** (Completed), **TASK-0005**, and **TASK-0006**.
    *   **Drill-down**: See `project_requirements.md` and `requirement_ops.md`.
*   **REQ-0003: Source Traceability** (Active)
    *   **Focus**: Mandates field-level source mapping and standardized credibility scores for key conclusions (e.g., opportunity status, hit rates, valuation sources).
    *   **Relationship**: Supersedes **REQ-0001** (M2 opportunity validation report).
    *   **Linked Tasks**: **TASK-0007**, **TASK-0008**, and **TASK-0009**.
    *   **Drill-down**: See `project_requirements.md`.

### Operational Rules & Constraints
1.  **Traceability**: Maintain field-level traceability for all DCF, external valuations, and opportunity validations.
2.  **User Transparency**: Users must be able to judge the origin and reliability of every key conclusion via source labeling.
3.  **Non-Goals**: The system will not generate automated trading orders or use untraceable sample data for production standards.
4.  **Compatibility**: Opportunity packs must remain compatible with the three-market output rhythm and reuse `run_real_pack_3markets.sh` products.

### Key Files & Task Notes
*   **requirements.md**: Canonical requirements, goals, and constraints registry.
*   **TASK-0004.md**: Documentation of completed scope and downgrade rules for REQ-0002.
*   **context.md**: Summary index of active requirements and tasks.