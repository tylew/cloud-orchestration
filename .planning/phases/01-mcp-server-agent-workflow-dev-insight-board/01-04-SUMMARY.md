---
phase: 01-mcp-server-agent-workflow-dev-insight-board
plan: 04
subsystem: mcp
tags: [mcp, node-crud, auto-provisioning, iam, validation]

requires:
  - phase: 01-01
    provides: MCP server scaffold with FastMCP instance and tool registration pattern
  - phase: 01-02
    provides: auto_provision_for_node() and infer_iam_roles() functions
provides:
  - 4 MCP node CRUD tools (add_node, update_node, delete_node, list_nodes)
  - Auto-provisioning integration for compute nodes via MCP
  - IAM role recomputation on dependency changes
  - Validation persistence after every node mutation
affects: [01-05, 01-06, deploy-pipeline, agent-workflow]

tech-stack:
  added: []
  patterns: [lazy-dependency-loading, module-level-globals-for-testability]

key-files:
  created:
    - packages/mcp/tools/nodes.py
    - packages/tests/test_mcp_nodes.py
  modified:
    - packages/mcp/server.py

key-decisions:
  - "Lazy-load GCP SDK dependencies via _ensure_deps() to avoid import-time initialization in tests"
  - "Module-level globals for blueprint_store/auto_provision_for_node/infer_iam_roles enable clean mocking"

patterns-established:
  - "Lazy dependency pattern: module-level None globals + _ensure_deps() for GCP SDK isolation"
  - "Node tool response pattern: {node, auto_created, validation, warnings}"

requirements-completed: [AGT-02, AGT-08, AGT-09, AGT-10]

duration: 5min
completed: 2026-03-27
---

# Phase 01 Plan 04: Node CRUD MCP Tools Summary

**4 MCP node CRUD tools with auto-provisioning integration -- add_node auto-creates SA and networking, all mutations trigger validation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-27T06:04:55Z
- **Completed:** 2026-03-27T06:10:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented add_node, update_node, delete_node, list_nodes as MCP tools
- add_node integrates auto_provision_for_node() and returns auto_created nodes (D-09)
- update_node recomputes IAM roles via infer_iam_roles() when depends_on changes
- delete_node warns about auto-provisioned node deletion (D-10)
- All mutations run validate_blueprint_by_slug and persist results (D-21)
- 8 unit tests with mocked store layer all passing

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `13ea4f6` (test)
2. **Task 1 (GREEN): Node CRUD tools + passing tests** - `3771c0a` (feat)
3. **Task 2: Register nodes in MCP server** - `7c2fbf5` (chore)

_TDD task had RED and GREEN commits._

## Files Created/Modified
- `packages/mcp/tools/nodes.py` - 4 MCP tools for node CRUD with auto-provisioning
- `packages/tests/test_mcp_nodes.py` - 8 unit tests covering all tools and edge cases
- `packages/mcp/server.py` - Added nodes import to tool registration

## Decisions Made
- Used lazy dependency loading (_ensure_deps pattern) to avoid import-time GCP SDK initialization. This is necessary because the schema/validation modules import google-cloud libraries.
- Used module-level globals (blueprint_store, auto_provision_for_node, infer_iam_roles) instead of inline imports so tests can cleanly patch them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy-load pattern for GCP SDK dependencies**
- **Found during:** Task 1 (test execution)
- **Issue:** Direct imports of auto_provision and iam_mappings fail in worktree because schemas/enums.py not committed to git (untracked in main repo)
- **Fix:** Changed from top-level imports to lazy-load pattern with _ensure_deps() and module-level globals
- **Files modified:** packages/mcp/tools/nodes.py, packages/tests/test_mcp_nodes.py
- **Verification:** All 8 tests pass
- **Committed in:** 3771c0a (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Import pattern change was necessary for testability. No scope creep.

## Issues Encountered
None beyond the import-time dependency issue documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all tools are fully wired to store layer and auto-provisioning.

## Next Phase Readiness
- Node CRUD tools are ready for agent workflow integration
- All 11 MCP tools now registered (3 project + 4 blueprint + 4 node)
- Auto-provisioning and IAM inference fully integrated into the add/update flow

---
*Phase: 01-mcp-server-agent-workflow-dev-insight-board*
*Completed: 2026-03-27*
