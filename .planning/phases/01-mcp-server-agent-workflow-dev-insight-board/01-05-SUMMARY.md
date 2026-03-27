---
phase: 01-mcp-server-agent-workflow-dev-insight-board
plan: 05
subsystem: mcp
tags: [mcp, secrets, code-files, cloud-build, deploy, concurrency-guards, gcs, secret-manager]

requires:
  - phase: 01-01
    provides: MCP server with FastMCP, context module, project/blueprint/node tools
  - phase: 01-04
    provides: Auto-provisioning and IAM inference tools

provides:
  - Secret management MCP tools (create, list, get, delete)
  - Code file management MCP tools (write, read, list, delete)
  - Container build MCP tools (trigger, status, logs, list)
  - Deploy operation MCP tools (trigger, status, logs, list)
  - Concurrency guards for builds and deploys (D-19)
  - Validation gate for deploys (D-21)

affects: [01-06, dev-insight-board]

tech-stack:
  added: [threading.Thread for background deploy/build outside ASGI]
  patterns: [lazy-loaded module-level deps for testability, GCP project ID resolution chain, concurrency guard pattern with actionable errors]

key-files:
  created:
    - packages/mcp/tools/secrets.py
    - packages/mcp/tools/code_files.py
    - packages/mcp/tools/builds.py
    - packages/mcp/tools/deploy.py
    - packages/tests/test_mcp_tools_secrets_code.py
    - packages/tests/test_mcp_tools_ops.py
  modified:
    - packages/mcp/server.py

key-decisions:
  - "Secret tools use projects_store.get_env_entry to resolve GCP project ID from environment entry"
  - "Code file tools pass project_ref_id directly to GCS storage (matching handler pattern)"
  - "trigger_deploy uses threading.Thread(daemon=True) for background orchestration outside ASGI context"
  - "get_build_logs retrieves TF plan/apply from GCS via existing cloud_build.py functions"
  - "In-progress builds/deploys return status + log_url without attempting log retrieval"

patterns-established:
  - "GCP project resolution: project -> env_entry -> gcp_project_id (reusable _resolve_gcp_project helper)"
  - "Concurrency guard: check latest record status before allowing new operation, return actionable error"
  - "Background thread pattern: threading.Thread(target=_run_fn, daemon=True).start() for MCP context"

requirements-completed: [AGT-03, AGT-04, AGT-05, AGT-06]

duration: 6min
completed: 2026-03-27
---

# Phase 01 Plan 05: Operational MCP Tools Summary

**16 operational MCP tools for secrets, code files, builds, and deploys with concurrency guards and validation gating**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-27T06:14:10Z
- **Completed:** 2026-03-27T06:20:25Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- 4 secret management tools wrapping Secret Manager + Firestore metadata store
- 4 code file tools wrapping GCS storage for compute node source files
- 4 container build tools with in-progress concurrency guards
- 4 deploy tools with concurrency, validation, and provisioning gates
- 18 tests covering CRUD operations, concurrency guards, log retrieval, error handling
- Server.py now imports all 7 tool modules (27 total tools registered)

## Task Commits

Each task was committed atomically:

1. **Task 1: Secret management and code file MCP tools with tests** (TDD)
   - `c30ef51` (test) - RED: failing tests for secrets and code files
   - `00b0b5f` (feat) - GREEN: implement secrets and code file tools
2. **Task 2: Build and deploy MCP tools with concurrency guards** - `c988272` (feat)

## Files Created/Modified
- `packages/mcp/tools/secrets.py` - 4 secret tools (create, list, get, delete) with GCP project resolution
- `packages/mcp/tools/code_files.py` - 4 code file tools (write, read, list, delete) wrapping GCS
- `packages/mcp/tools/builds.py` - 4 build tools (trigger, status, logs, list) with concurrency guard
- `packages/mcp/tools/deploy.py` - 4 deploy tools (trigger, status, logs, list) with validation gate
- `packages/mcp/server.py` - Updated imports to register all 7 tool modules
- `packages/tests/test_mcp_tools_secrets_code.py` - 11 tests for secret and code file tools
- `packages/tests/test_mcp_tools_ops.py` - 7 tests for build and deploy tools

## Decisions Made
- Secret tools resolve GCP project ID through the existing env entry pattern (project -> environments[] -> gcp_project_id)
- Code file tools use project_ref_id as the GCS path identifier, matching the handler pattern
- Deploy uses threading.Thread(daemon=True) instead of FastAPI BackgroundTasks since MCP runs outside ASGI
- get_build_logs skips GCS log retrieval for in-progress builds, returning status + log_url instead
- create_secret deliberately omits the secret value from its response for security

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 27 MCP tools now registered covering full infrastructure lifecycle
- Agent can manage projects, blueprints, nodes, secrets, code files, builds, and deploys
- Ready for end-to-end testing with the actual MCP server

---
*Phase: 01-mcp-server-agent-workflow-dev-insight-board*
*Completed: 2026-03-27*
