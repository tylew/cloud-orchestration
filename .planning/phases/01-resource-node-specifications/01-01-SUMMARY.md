---
phase: 01-resource-node-specifications
plan: 01
subsystem: infra
tags: [terraform, lifecycle, mutability, compute, security, external, gcp]

# Dependency graph
requires: []
provides:
  - Shared lifecycle archetype definitions (Simple CRUD, Compute with Image, Parent-Child Composite, Network with Dependencies)
  - Complete field classification for 6 node types (cloud_run, cloud_run_job, cloud_function, service_account, secret_manager, third_party_api)
  - ForceNew field inventory per Terraform provider ~5.0
  - Platform-only vs TF-mapped field separation pattern
affects: [01-02-PLAN, 01-03-PLAN, phase-02, phase-03, phase-06, phase-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-tier spec structure: rigid template, narrative patterns, type-specific details"
    - "Lifecycle archetype mapping: each node type assigned to exactly one archetype"
    - "Field classification table: Field | Type | Required | Default | Mutable | TF Argument | Validation"

key-files:
  created:
    - .planning/phases/01-resource-node-specifications/specs/00-lifecycle-archetypes.md
    - .planning/phases/01-resource-node-specifications/specs/compute/01-compute-template.md
    - .planning/phases/01-resource-node-specifications/specs/compute/02-compute-patterns.md
    - .planning/phases/01-resource-node-specifications/specs/compute/03-cloud-run.md
    - .planning/phases/01-resource-node-specifications/specs/compute/04-cloud-run-job.md
    - .planning/phases/01-resource-node-specifications/specs/compute/05-cloud-function.md
    - .planning/phases/01-resource-node-specifications/specs/security/01-security-template.md
    - .planning/phases/01-resource-node-specifications/specs/security/02-security-patterns.md
    - .planning/phases/01-resource-node-specifications/specs/security/03-service-account.md
    - .planning/phases/01-resource-node-specifications/specs/security/04-secret-manager.md
    - .planning/phases/01-resource-node-specifications/specs/external/01-external-template.md
    - .planning/phases/01-resource-node-specifications/specs/external/02-external-patterns.md
    - .planning/phases/01-resource-node-specifications/specs/external/03-third-party-api.md
  modified: []

key-decisions:
  - "Four lifecycle archetypes defined: Simple CRUD, Compute with Image, Parent-Child Composite, Network with Dependencies plus Non-Terraform special case"
  - "Revision-creating updates classified separately from mutable/ForceNew -- Cloud Run template changes create revisions, not in-place updates"
  - "Cloud Function runtime/entry_point marked as MEDIUM confidence mutable -- Terraform docs ambiguous, GCP API likely allows updates"
  - "third_party_api field inventory corrected: Pydantic model has 7 fields (provider, base_url, auth_method, secret_ref, rate_limit, timeout_ms, description) vs plan's 6"

patterns-established:
  - "Archetype reference pattern: category specs reference 00-lifecycle-archetypes.md rather than duplicating state machines"
  - "Field classification split: Terraform-mapped fields section (with Mutable column) + Platform-only fields section (always mutable)"
  - "ForceNew documentation: each type lists ForceNew fields with impact description and TF provider version citation"

requirements-completed: [RSLC-01, RSLC-02, RSLC-03]

# Metrics
duration: 12min
completed: 2026-03-27
---

# Phase 01 Plan 01: Compute, Security, and External Node Specifications Summary

**Lifecycle archetypes framework with complete field classification for 6 node types across compute, security, and external categories per Terraform provider ~5.0**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-27T00:39:00Z
- **Completed:** 2026-03-27T00:50:47Z
- **Tasks:** 2
- **Files created:** 13

## Accomplishments

- Defined 4 lifecycle archetypes + 1 special case with shared platform state machine covering all 22 node types
- Documented complete field classification for 6 types: cloud_run (~28 fields), cloud_run_job (~18 fields), cloud_function (~17 fields), service_account (4 fields), secret_manager (11 fields), third_party_api (7 fields)
- Classified ForceNew fields per Terraform provider ~5.0 for all Terraform-backed types
- Established three-tier spec pattern (template, patterns, specifics) that Plan 02 and 03 will follow

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lifecycle archetypes doc + Compute category specs** - `3a99fc3` (feat)
2. **Task 2: Create Security/Identity and External category specs** - `25eca69` (feat)

## Files Created

- `specs/00-lifecycle-archetypes.md` - Shared lifecycle archetype definitions with platform state machine table
- `specs/compute/01-compute-template.md` - Rigid template: field classification for cloud_run, cloud_run_job, cloud_function
- `specs/compute/02-compute-patterns.md` - Shared compute behaviors: revision model, VPC access, scaling patterns
- `specs/compute/03-cloud-run.md` - Cloud Run specifics: traffic splitting, probes, volumes, GPU, session affinity, Eventarc
- `specs/compute/04-cloud-run-job.md` - Cloud Run Job specifics: task_count, parallelism, scheduler triggers
- `specs/compute/05-cloud-function.md` - Cloud Function specifics: source upload, event triggers, build config, 6 ForceNew fields
- `specs/security/01-security-template.md` - Rigid template: field classification for service_account, secret_manager
- `specs/security/02-security-patterns.md` - IAM scope differences, secret value lifecycle, deletion protection
- `specs/security/03-service-account.md` - Service Account specifics: account_id naming, email derivation, compute references
- `specs/security/04-secret-manager.md` - Secret Manager specifics: replication immutability, dual lifecycle, version management
- `specs/external/01-external-template.md` - Rigid template: all 7 platform-only fields for third_party_api
- `specs/external/02-external-patterns.md` - No TF resource pattern, graph visualization purpose, TF skip behavior
- `specs/external/03-third-party-api.md` - Third-Party API specifics: RateLimit sub-model, future AI agent context

## Decisions Made

- **Four archetypes + 1 special case:** Covers all 22 node types without redundancy. Archetype reference pattern prevents state machine duplication.
- **Revision-creating as distinct update path:** Compute types have three update paths (mutable in-place, revision-creating, ForceNew destroy-recreate) vs Simple CRUD's two (mutable, ForceNew).
- **MEDIUM confidence on CF runtime/entry_point:** Marked as likely mutable based on GCP API behavior, but Terraform docs are ambiguous. Flagged for verification.
- **third_party_api field count correction:** Pydantic model has 7 fields (including `provider` and `timeout_ms`) vs plan's reference to 6 fields. Documented the actual model.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all specifications are complete design documents with no placeholder content.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Archetype framework established -- Plan 02 (Data/Messaging) and Plan 03 (Network) can reference 00-lifecycle-archetypes.md
- Three-tier spec pattern proven -- subsequent plans follow the same template/patterns/specifics structure
- All ForceNew research from RESEARCH.md consumed for compute, security, and external categories; remaining data/messaging/network research available for Plans 02 and 03

---
*Phase: 01-resource-node-specifications*
*Completed: 2026-03-27*

## Self-Check: PASSED

All 13 spec files verified present. All 1 summary file present. Commits 3a99fc3 and 25eca69 verified in git log.
