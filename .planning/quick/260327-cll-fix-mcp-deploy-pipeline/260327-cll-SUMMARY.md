---
phase: quick
plan: 260327-cll
subsystem: mcp
tags: [mcp, deploy, blueprint, firestore, envelope]

provides:
  - "Working MCP validate/preview/deploy tools that reconstruct Envelope from node subcollection"
  - "Deploy pipeline persists blueprint doc before launching orchestrator"
  - "Firestore composite index for deploys collection queries"
affects: [mcp-tools, deploy-pipeline]

tech-stack:
  added: []
  patterns:
    - "Envelope reconstruction from list_nodes for MCP tools (matching nodes.py pattern)"
    - "Pre-deploy blueprint persistence via save_env_blueprint for orchestrator compatibility"

key-files:
  created: []
  modified:
    - packages/mcp/tools/blueprint.py
    - packages/mcp/tools/deploy.py
    - docker-compose.yml
    - firestore.indexes.json

key-decisions:
  - "Reuse node_dicts for both validation gate and save_env_blueprint to avoid double Firestore reads"
  - "Use real gcp_project_id/region (not placeholder) when persisting blueprint for deploy orchestrator"

requirements-completed: []

duration: 2min
completed: 2026-03-27
---

# Quick Fix 260327-cll: Fix MCP Deploy Pipeline Summary

**MCP blueprint/deploy tools reconstructed to use node subcollection instead of missing parent doc, with pre-deploy blueprint persistence for orchestrator compatibility**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T16:08:10Z
- **Completed:** 2026-03-27T16:10:34Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed validate_blueprint, preview_terraform, and trigger_deploy to reconstruct Envelope from node subcollection via list_nodes instead of relying on get_env_blueprint (which fails when nodes are added individually via MCP)
- Added save_env_blueprint call in trigger_deploy to persist a full blueprint doc before launching the deploy orchestrator
- Added DEV_TENANT_ID and DEV_USER_EMAIL env vars to docker-compose.yml for MCP tenant context
- Added Firestore composite index for deploys collection (project_id + created_at DESC)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix MCP blueprint and deploy tools** - `4003efe` (fix)
2. **Task 2: Add env vars and Firestore composite index** - `3052dc1` (chore)

## Files Created/Modified
- `packages/mcp/tools/blueprint.py` - validate_blueprint and preview_terraform now reconstruct Envelope from list_nodes
- `packages/mcp/tools/deploy.py` - validation gate uses list_nodes; persists blueprint via save_env_blueprint before orchestrator launch
- `docker-compose.yml` - DEV_TENANT_ID and DEV_USER_EMAIL passed to app service
- `firestore.indexes.json` - Added deploys composite index (project_id ASC + created_at DESC)
- `.env.local` - Added DEV_TENANT_ID and DEV_USER_EMAIL (gitignored, not committed)

## Decisions Made
- Reuse node_dicts variable for both validation gate and save_env_blueprint call to avoid double Firestore reads in trigger_deploy
- Use real gcp_project_id and region from env entry (not "validation" placeholder) when persisting blueprint for deploy orchestrator, since the orchestrator needs accurate global config

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `.env.local` is in `.gitignore` so changes to it cannot be committed. The env vars are documented and the docker-compose.yml explicit environment entries ensure they propagate regardless.

## User Setup Required
After pulling these changes, update your local `.env.local` with:
```
DEV_TENANT_ID=yBi9vPkZ5HXNw7zyfSr7zltjojC2
DEV_USER_EMAIL=tyler@pl4m.com
```

Deploy the Firestore index:
```
firebase deploy --only firestore:indexes
```

## Next Phase Readiness
- MCP deploy pipeline is now unblocked for end-to-end testing
- The deploy orchestrator will work correctly since trigger_deploy now persists the blueprint doc it needs

---
*Quick: 260327-cll-fix-mcp-deploy-pipeline*
*Completed: 2026-03-27*

## Self-Check: PASSED
