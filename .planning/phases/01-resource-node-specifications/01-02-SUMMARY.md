---
phase: 01-resource-node-specifications
plan: 02
subsystem: infra
tags: [terraform, cloud-sql, firestore, bigquery, bigtable, gcs, lifecycle, mutability]

# Dependency graph
requires:
  - phase: 01-resource-node-specifications (01-RESEARCH)
    provides: ForceNew field classifications per Terraform provider ~5.0
provides:
  - Complete field classification tables for 5 data/storage parent types
  - Inline child type documentation for 4 child types (cloud_sql_database, cloud_sql_table, firestore_collection, bigquery_table)
  - Parent-child lifecycle cascade documentation
  - Data loss risk analysis for ForceNew field changes on stateful resources
  - IAM scope variation documentation across data types
affects: [02-dependency-convention-rules, 03-deploy-engine, 04-safety, 06-iam, 08-database-lifecycle]

# Tech tracking
tech-stack:
  added: []
  patterns: [three-tier-spec-structure, parent-child-composite-archetype, field-classification-table]

key-files:
  created:
    - .planning/phases/01-resource-node-specifications/specs/data/01-data-template.md
    - .planning/phases/01-resource-node-specifications/specs/data/02-data-patterns.md
    - .planning/phases/01-resource-node-specifications/specs/data/03-cloud-sql.md
    - .planning/phases/01-resource-node-specifications/specs/data/04-firestore.md
    - .planning/phases/01-resource-node-specifications/specs/data/05-bigquery.md
    - .planning/phases/01-resource-node-specifications/specs/data/06-bigtable.md
    - .planning/phases/01-resource-node-specifications/specs/data/07-gcs-bucket.md
  modified: []

key-decisions:
  - "Treated GCS Bucket (Storage category) together with Data types since they share lifecycle characteristics"
  - "Documented inline vs flat node dual-path for child resources (both approaches generate TF resources)"
  - "Flagged retention_policy.is_locked as irreversible operation requiring special UX treatment"

patterns-established:
  - "Field Classification table split: Terraform-mapped fields (with mutability) + Platform-only fields (always mutable per D-09)"
  - "ForceNew Summary section per type for quick reference"
  - "Data loss implication callouts for stateful resources"

requirements-completed: [RSLC-01, RSLC-02, RSLC-03]

# Metrics
duration: 8min
completed: 2026-03-27
---

# Phase 01 Plan 02: Data Category Specifications Summary

**Complete field classification and lifecycle documentation for 5 data/storage types and 4 child types with ForceNew analysis against Terraform provider ~5.0**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T00:39:18Z
- **Completed:** 2026-03-27T00:48:04Z
- **Tasks:** 2
- **Files created:** 7

## Accomplishments

- Created rigid template with Field Classification tables for all 5 parent types (cloud_sql: 12 fields, firestore: 8 fields, bigquery: 12 fields, bigtable: 5 fields, gcs_bucket: 10 fields)
- Documented all 4 child types inline under their parents: cloud_sql_database (TF resource), cloud_sql_table (platform-only), firestore_collection (platform-only), bigquery_table (TF resource)
- Created comprehensive patterns document covering parent-child cascade behavior, deletion protection, data loss risk, and IAM scope variation
- Created 5 specifics documents with type-specific edge cases, nested sub-model details, TF template analysis, and integration points

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Data category rigid template and patterns docs** - `ce9b893` (docs)
2. **Task 2: Create Data category specifics docs for all 5 types** - `850b17f` (docs)

## Files Created

- `.planning/phases/01-resource-node-specifications/specs/data/01-data-template.md` - Rigid template with Field Classification tables for all 5 parent types + 4 child types inline
- `.planning/phases/01-resource-node-specifications/specs/data/02-data-patterns.md` - Shared patterns: parent-child lifecycle, deletion protection, data loss risk, IAM scope variation
- `.planning/phases/01-resource-node-specifications/specs/data/03-cloud-sql.md` - Cloud SQL specifics including cloud_sql_database and cloud_sql_table (3-level hierarchy)
- `.planning/phases/01-resource-node-specifications/specs/data/04-firestore.md` - Firestore specifics including firestore_collection with TTL field behavior
- `.planning/phases/01-resource-node-specifications/specs/data/05-bigquery.md` - BigQuery specifics including bigquery_table with partitioning and schema evolution
- `.planning/phases/01-resource-node-specifications/specs/data/06-bigtable.md` - Bigtable specifics with cluster-level ForceNew and PRODUCTION vs DEVELOPMENT types
- `.planning/phases/01-resource-node-specifications/specs/data/07-gcs-bucket.md` - GCS Bucket specifics with globally unique naming, lifecycle rules, retention policy

## Decisions Made

- Treated GCS Bucket (categorized as "Storage" in REGISTRY) together with Data types since they share lifecycle characteristics (stateful, data loss risk, deletion protection patterns)
- Documented the dual-path for child resources: inline definitions on parent config vs flat child nodes in the blueprint, noting both generate TF resources
- Flagged `retention_policy.is_locked` on GCS Bucket as an irreversible operation that needs special UX treatment in the platform
- Noted that the GCS Bucket TF template is missing `retention_policy`, `encryption`, and `logging` blocks compared to the Pydantic model

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all specifications are complete documentation artifacts with no code stubs.

## Next Phase Readiness

- Data category specifications complete, ready for downstream phases
- Phase 2 (Dependency & Convention Rules) can reference data type inter-resource dependency edges
- Phase 4 (Safety) has data loss risk documentation for ForceNew field safety gates
- Phase 6 (IAM) has IAM scope variation documented for all data types
- Phase 8 (Database Lifecycle) has the foundation for database provisioning + schema management

## Self-Check: PASSED

- All 7 spec files exist in specs/data/
- SUMMARY.md exists
- Commit ce9b893 found (Task 1)
- Commit 850b17f found (Task 2)

---
*Phase: 01-resource-node-specifications*
*Completed: 2026-03-27*
