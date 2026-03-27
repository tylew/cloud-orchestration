---
phase: 01-mcp-server-agent-workflow-dev-insight-board
plan: 02
subsystem: core
tags: [iam, auto-provisioning, service-account, vpc, networking, tdd]

requires:
  - phase: none
    provides: standalone pure-logic modules using existing enums

provides:
  - IAM_ROLE_MAP with 16 ActionType x NodeType -> GCP IAM role mappings
  - PRIVATE_ACCESS_TYPES set for VPC connectivity inference
  - get_iam_role() single-lookup and infer_iam_roles() graph-wide inference
  - auto_provision_for_node() orchestration for SA + networking creation

affects: [01-04-plan, mcp-node-tools, terraform-generation]

tech-stack:
  added: []
  patterns: [pure-logic-modules, dict-based-node-data, tdd-red-green]

key-files:
  created:
    - packages/core/iam_mappings.py
    - packages/core/auto_provision.py
    - packages/tests/test_iam_mappings.py
    - packages/tests/test_auto_provision.py
  modified: []

key-decisions:
  - "IAM_ROLE_MAP uses string tuples (action, type) for fast O(1) lookup"
  - "PRIVATE_ACCESS_TYPES limited to Cloud SQL and Bigtable per D-11 research"
  - "Networking uses fixed names (default-vpc, default-subnet, default-connector) for dedup"
  - "depends_on mutated in-place to add SA and connector slugs"

patterns-established:
  - "Auto-provisioned nodes tagged with auto_provisioned: True for traceability"
  - "Implicit Read inference from depends_on when no explicit internalGraph steps"
  - "VPC existence check prevents duplicate networking creation"

requirements-completed: [AGT-08, AGT-09, AGT-10]

duration: 4min
completed: 2026-03-27
---

# Phase 01 Plan 02: Auto-Provisioning Intelligence Summary

**IAM role inference from dependency graph edges and auto-creation of service accounts + VPC networking for compute nodes via pure-logic modules with 48 TDD tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T05:52:03Z
- **Completed:** 2026-03-27T05:56:12Z
- **Tasks:** 4 (TDD: 2 RED + 2 GREEN)
- **Files created:** 4

## Accomplishments
- IAM_ROLE_MAP covering all 16 ActionType x NodeType combinations from the research
- infer_iam_roles() resolves roles from node dependency graph including implicit Read from depends_on
- auto_provision_for_node() creates service accounts for all compute types and VPC/subnet/connector for Cloud SQL and Bigtable deps
- No duplicate VPC/subnet/connector creation when networking already exists
- All 48 tests pass with zero external dependencies (pure logic, no Firestore)

## Task Commits

Each task was committed atomically (TDD flow):

1. **RED: IAM mapping tests** - `c5b548d` (test)
2. **GREEN: IAM mapping implementation** - `58c4e9b` (feat)
3. **RED: Auto-provisioning tests** - `a45f367` (test)
4. **GREEN: Auto-provisioning implementation** - `26e5fc0` (feat)

## Files Created/Modified
- `packages/core/iam_mappings.py` - IAM_ROLE_MAP table, get_iam_role(), infer_iam_roles(), PRIVATE_ACCESS_TYPES
- `packages/core/auto_provision.py` - auto_provision_for_node() with SA and networking auto-creation
- `packages/tests/test_iam_mappings.py` - 28 tests for role mapping and inference
- `packages/tests/test_auto_provision.py` - 20 tests for auto-provisioning logic

## Decisions Made
- IAM_ROLE_MAP uses string tuples (action, type) as keys for O(1) lookup rather than nested dicts
- PRIVATE_ACCESS_TYPES limited to Cloud SQL and Bigtable per D-11 research decision
- Networking nodes use fixed names (default-vpc, default-subnet, default-connector) to enable simple dedup
- depends_on is mutated in-place on the node_data dict so the caller sees the updated dependencies

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- iam_mappings.py and auto_provision.py are ready to be imported by MCP node tools in Plan 04
- Key link: `from packages.core.iam_mappings import IAM_ROLE_MAP, infer_iam_roles`
- Key link: `from packages.core.auto_provision import auto_provision_for_node`

## Self-Check: PASSED

All 4 created files verified. All 4 commit hashes verified.

---
*Phase: 01-mcp-server-agent-workflow-dev-insight-board*
*Completed: 2026-03-27*
