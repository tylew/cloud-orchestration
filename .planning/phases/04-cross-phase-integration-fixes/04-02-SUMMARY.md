---
phase: 04-cross-phase-integration-fixes
plan: 02
subsystem: api
tags: [terraform, output-parsing, deploy-orchestrator]

# Dependency graph
requires:
  - phase: 03-terraform-output-surfacing-and-post-deploy-user-action-guidance
    provides: _parse_terraform_outputs function and deploy output pipeline
provides:
  - Node-name-aware _parse_terraform_outputs with correct multi-underscore grouping
  - Tests for multi-underscore output names (name_servers, connection_name, private_ip)
affects: [deploy-pipeline, mcp-tools]

# Tech tracking
tech-stack:
  added: []
  patterns: [longest-prefix-first matching for output name splitting]

key-files:
  created: []
  modified:
    - packages/platform/deploy_orchestrator.py
    - packages/tests/test_terraform_outputs.py

key-decisions:
  - "Longest-first prefix matching against known node names for greedy output name splitting"
  - "Backward-compatible rsplit fallback when node_names not provided"

patterns-established:
  - "Prefix matching: sort names longest-first, match prefix+underscore to split multi-underscore keys"

requirements-completed: [OUT-04]

# Metrics
duration: 3min
completed: 2026-03-29
---

# Phase 04 Plan 02: Fix Multi-Underscore Terraform Output Parsing Summary

**Node-name-aware prefix matching in _parse_terraform_outputs to correctly group multi-underscore outputs like name_servers, connection_name, and private_ip**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-29T01:16:10Z
- **Completed:** 2026-03-29T01:19:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed by_node grouping for multi-underscore Terraform output names (name_servers, connection_name, private_ip)
- Added node_names parameter to _parse_terraform_outputs with longest-first prefix matching
- Updated _run_deploy call site to extract node names from blueprint envelope
- Maintained backward compatibility via rsplit fallback when node_names not provided
- All 223 unit tests pass (29 in test_terraform_outputs.py including 3 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for multi-underscore by_node parsing** - `c611277` (test)
2. **Task 2: Implement node-name-aware output parsing and update call site** - `895f628` (feat)

_Note: TDD task 1 = RED phase, task 2 = GREEN phase_

## Files Created/Modified
- `packages/platform/deploy_orchestrator.py` - Added node_names param, longest-first prefix matching, updated _run_deploy call site
- `packages/tests/test_terraform_outputs.py` - Added 3 new tests for multi-underscore, with_node_names, and fallback scenarios

## Decisions Made
- Used longest-first prefix matching (sorted by name length descending) to avoid ambiguity when node names overlap
- Kept rsplit("_", 1) as fallback for backward compatibility when node_names is not provided

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Multi-underscore output parsing now correct for Cloud DNS name_servers, Cloud SQL connection_name/private_ip
- Deploy pipeline passes node names from envelope to parser automatically

---
*Phase: 04-cross-phase-integration-fixes*
*Completed: 2026-03-29*
