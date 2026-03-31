---
id: T01
parent: S02
milestone: M003
provides: []
requires: []
affects: []
key_files: ["apps/web/src/App.tsx", "apps/web/src/types/node.ts", "archive/web-insight/"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "rg 'insight' apps/web/src/ returns zero hits. rg for config ID fields returns zero hits. archive/web-insight/ contains exactly 9 files. vite build succeeds cleanly."
completed_at: 2026-03-31T16:52:55.504Z
blocker_discovered: false
---

# T01: Archive 9 insight dead-code files, remove insight route from App.tsx, add optional id/resource_id to BaseNode type

> Archive 9 insight dead-code files, remove insight route from App.tsx, add optional id/resource_id to BaseNode type

## What Happened
---
id: T01
parent: S02
milestone: M003
key_files:
  - apps/web/src/App.tsx
  - apps/web/src/types/node.ts
  - archive/web-insight/
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-31T16:52:55.504Z
blocker_discovered: false
---

# T01: Archive 9 insight dead-code files, remove insight route from App.tsx, add optional id/resource_id to BaseNode type

**Archive 9 insight dead-code files, remove insight route from App.tsx, add optional id/resource_id to BaseNode type**

## What Happened

Moved 9 insight-related files (InsightBoard screen, insight-store, 7 insight components) to archive/web-insight/. Removed the InsightBoard import and /insight/:projectRefId route from App.tsx. Added optional id and resource_id fields to the frontend BaseNode type in types/node.ts. Vite build succeeds, zero insight references remain in apps/web/src/.

## Verification

rg 'insight' apps/web/src/ returns zero hits. rg for config ID fields returns zero hits. archive/web-insight/ contains exactly 9 files. vite build succeeds cleanly.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg -c 'insight' apps/web/src/` | 1 | ✅ pass | 100ms |
| 2 | `ls archive/web-insight/ | wc -l` | 0 | ✅ pass | 100ms |
| 3 | `vite build` | 0 | ✅ pass | 2700ms |
| 4 | `slice verification composite` | 0 | ✅ pass | 200ms |


## Deviations

App.tsx had duplicate trailing content in worktree; rewrote cleanly. tsc has pre-existing TS6133 error in scroll-area.tsx unrelated to this task; verified via vite build instead.

## Known Issues

Pre-existing tsc error: scroll-area.tsx unused React import (TS6133).

## Files Created/Modified

- `apps/web/src/App.tsx`
- `apps/web/src/types/node.ts`
- `archive/web-insight/`


## Deviations
App.tsx had duplicate trailing content in worktree; rewrote cleanly. tsc has pre-existing TS6133 error in scroll-area.tsx unrelated to this task; verified via vite build instead.

## Known Issues
Pre-existing tsc error: scroll-area.tsx unused React import (TS6133).
