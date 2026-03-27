---
phase: 01-mcp-server-agent-workflow-dev-insight-board
plan: 03
subsystem: api, ui
tags: [fastapi, debug, firestore, zustand, react, insight-board]

requires:
  - phase: none
    provides: existing API handlers and store modules
provides:
  - 5 debug API endpoints at /api/debug/* for raw state inspection
  - InsightBoard screen at /insight/:projectRefId with Firestore subscriptions
  - Zustand insight store with 4 real-time Firestore subscriptions
  - list_deploys function in deploys store
affects: [01-05-mcp-tools, 01-06-insight-panels]

tech-stack:
  added: []
  patterns: [debug-endpoint-pattern, firestore-subscription-store]

key-files:
  created:
    - packages/api/handlers/debug.py
    - packages/tests/test_debug_endpoints.py
    - apps/web/src/screens/InsightBoard.tsx
    - apps/web/src/stores/insight-store.ts
  modified:
    - packages/api/main.py
    - packages/platform/store/deploys.py
    - apps/web/src/App.tsx

key-decisions:
  - "Debug endpoints use viewer-level auth via require_project_access for security"
  - "Terraform endpoint compiles on-the-fly rather than caching for always-fresh output"
  - "InsightBoard uses 4 Firestore subscriptions (project, nodes, validation, activity)"

patterns-established:
  - "Debug endpoint pattern: raw Firestore doc passthrough with viewer auth"
  - "Insight store pattern: module-level unsubscriber array for Firestore cleanup"

requirements-completed: [AGT-12, AGT-11]

duration: 6min
completed: 2026-03-27
---

# Phase 1 Plan 3: Debug Endpoints and Insight Board Scaffold Summary

**5 debug API endpoints for raw state inspection plus InsightBoard frontend scaffold with Firestore real-time subscriptions**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-27T05:53:08Z
- **Completed:** 2026-03-27T05:59:20Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- 5 debug endpoints under /api/debug/* returning raw project state, validation, terraform, deploys, and node status
- InsightBoard screen at /insight/:projectRefId with two-column grid layout and environment switching
- Zustand store subscribing to 4 Firestore paths (project doc, nodes, validation, activity) with real-time updates
- 8 unit tests covering all debug endpoints with mocked store calls

## Task Commits

Each task was committed atomically:

1. **Task 1: Debug API endpoints (TDD RED)** - `a78be5d` (test)
2. **Task 1: Debug API endpoints (TDD GREEN)** - `b9ff23e` (feat)
3. **Task 2: Insight Board frontend scaffold** - `30d9fa8` (feat)

## Files Created/Modified
- `packages/api/handlers/debug.py` - 5 debug endpoints for raw state inspection (AGT-12)
- `packages/api/main.py` - Debug router registration
- `packages/platform/store/deploys.py` - Added list_deploys() function
- `packages/tests/test_debug_endpoints.py` - 8 unit tests for debug endpoints
- `apps/web/src/screens/InsightBoard.tsx` - Insight board screen with placeholder panels
- `apps/web/src/stores/insight-store.ts` - Zustand store with 4 Firestore subscriptions
- `apps/web/src/App.tsx` - Added /insight/:projectRefId route

## Decisions Made
- Debug endpoints use viewer-level auth via require_project_access("viewer") for security
- Terraform endpoint compiles TF on-the-fly from blueprint rather than caching, ensuring fresh output
- InsightBoard uses module-level unsubscriber array pattern for Firestore subscription cleanup
- Skipped shadcn component installation (badge, card, scroll-area, separator) since scaffold only uses basic Tailwind -- Plan 06 will add them when panel components are built

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added list_deploys() to deploys store**
- **Found during:** Task 1 (Debug API endpoints)
- **Issue:** Plan references deploy_store.list_deploys() but function did not exist in deploys.py
- **Fix:** Added list_deploys() function that queries deploys by project_id, ordered by created_at desc
- **Files modified:** packages/platform/store/deploys.py
- **Verification:** Debug deploys endpoint test passes
- **Committed in:** b9ff23e (Task 1 commit)

**2. [Rule 3 - Blocking] Copied untracked dependency files to worktree**
- **Found during:** Task 1 (Test setup)
- **Issue:** Worktree only has git-tracked files; authz.py, deploys.py, schemas, and other modules needed for import resolution were missing
- **Fix:** Copied untracked files from main repo to worktree
- **Files modified:** ~70 files copied (not committed -- already exist in main repo)
- **Verification:** Tests import and run successfully

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Known Stubs

The InsightBoard screen contains 6 intentional placeholder panels with text "coming in Plan 06":
- `apps/web/src/screens/InsightBoard.tsx` line 68: "Project State Panel -- coming in Plan 06"
- `apps/web/src/screens/InsightBoard.tsx` line 72: "Resource List Panel -- coming in Plan 06"
- `apps/web/src/screens/InsightBoard.tsx` line 76: "Validation Panel -- coming in Plan 06"
- `apps/web/src/screens/InsightBoard.tsx` line 82: "Terraform Panel -- coming in Plan 06"
- `apps/web/src/screens/InsightBoard.tsx` line 86: "Deploy Panel -- coming in Plan 06"
- `apps/web/src/screens/InsightBoard.tsx` line 90: "Activity Feed -- coming in Plan 06"

These are intentional scaffolding. Plan 06 is explicitly responsible for implementing the panel components.

## Issues Encountered
- Worktree missing untracked files required for test execution -- resolved by copying from main repo
- Initial test mocking approach (patching require_project_access) didn't prevent real Firestore connections -- switched to patching find_project_for_user at the auth layer

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Debug endpoints ready for MCP tool wrapping (Plan 05)
- InsightBoard scaffold ready for panel implementation (Plan 06)
- Insight store subscriptions ready for panel data consumption

---
*Phase: 01-mcp-server-agent-workflow-dev-insight-board*
*Completed: 2026-03-27*
