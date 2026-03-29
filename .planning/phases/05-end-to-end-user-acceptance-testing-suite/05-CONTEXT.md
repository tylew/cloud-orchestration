# Phase 5: End-to-End User Acceptance Testing Suite - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a working end-to-end pipeline for **both** paths — agent (MCP) and human (UI) — to deploy infrastructure. Fix the two pre-existing bugs that block the deploy observation path. Write automated integration tests that prove the critical path works. Clean up REQUIREMENTS.md traceability.

**Not in scope:** Comprehensive error scenario testing, frontend unit tests, performance testing, new features.

</domain>

<decisions>
## Implementation Decisions

### Test Approach
- **D-01:** Automated integration tests that exercise the critical deploy path end-to-end. Not manual checklists — real pytest tests against live GCP (same pattern as existing integration tests in `packages/tests/integration/`).
- **D-02:** Tests cover the happy path only: add node -> configure -> validate -> deploy -> query outputs. Error scenarios are out of scope for this phase.
- **D-03:** Tests exercise both the MCP tool path (agent workflow) and the REST API path (what the UI calls). Both must complete the full pipeline.

### Bug Fixes (Pre-existing Issues)
- **D-04:** Fix `list_deploys` Firestore query mismatch. The query filters on `project_id == project_ref_id` but deploy records store `gcp_project_id`. This breaks deploy history lookup for both the debug API and MCP tools. Fix the query to use the correct field, and add a test proving it returns results.
- **D-05:** Fix `deployStatus` dead store field in `insight-store.ts`. The field is declared but never populated by any Firestore subscription. Either wire it to a real subscription or remove it and have DeployPanel use the debug API consistently. The goal is: the insight board must show deploy status without dead state.

### UI Requirements
- **D-06:** The insight board at `/insight/:projectRefId` must expose the full debug view of the deploy pipeline. All 6 panels (resource list, validation, terraform, deploy, activity, output) must render with real data from the target project.
- **D-07:** No new UI features — just fix what's broken (deployStatus) and verify existing panels work end-to-end with real deployed data.

### MCP Requirements
- **D-08:** The MCP server must be usable for the full critical path: `list_projects` -> `add_node` -> `configure_node` -> `validate_blueprint` -> `trigger_deploy` -> `get_deploy_status` -> `get_deploy_outputs`. Any tool in this chain that doesn't work gets fixed.
- **D-09:** Not all 27+ MCP tools need e2e testing — just the critical deploy path tools listed in D-08.

### REQUIREMENTS.md Cleanup
- **D-10:** Update traceability table to mark all Phase 4 gap closures as Complete. Verify all requirement statuses match actual codebase state.

### Claude's Discretion
- Test data setup and cleanup strategy (use existing test fixtures or create new ones)
- Specific Firestore field name to query in the list_deploys fix
- Whether deployStatus store field gets wired or removed (whichever is simpler)
- Integration test timeout values and skip conditions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deploy Pipeline (Critical Path)
- `packages/platform/deploy_orchestrator.py` -- `_run_deploy()` background task, TF output parsing
- `packages/platform/store/deploys.py` -- Deploy CRUD, `list_deploys()` with the broken query (D-04)
- `packages/platform/gcp/cloud_build.py` -- Cloud Build submission and output retrieval
- `packages/mcp/tools/deploy.py` -- MCP deploy tools (trigger_deploy, get_deploy_status, list_deploys, get_deploy_outputs)

### MCP Server
- `packages/mcp/tools/nodes.py` -- add_node, configure_node, list_nodes
- `packages/mcp/tools/blueprint.py` -- validate_blueprint, get_blueprint
- `packages/mcp/tools/projects.py` -- list_projects, get_project_status

### UI / Insight Board
- `apps/web/src/screens/InsightBoard.tsx` -- Main insight board screen
- `apps/web/src/stores/insight-store.ts` -- Zustand store with deployStatus dead field (D-05)
- `apps/web/src/components/insight/DeployPanel.tsx` -- Deploy panel using debug API fallback
- `apps/web/src/components/insight/ResourceListPanel.tsx` -- Resource list with deploy status badges

### Bug Context
- `.planning/v1.0-MILESTONE-AUDIT.md` -- Documents both pre-existing issues (list_deploys query, deployStatus field)
- `packages/api/handlers/debug.py` -- Debug endpoints the insight board calls

### Existing Tests (Patterns to Follow)
- `packages/tests/integration/test_api_deploy.py` -- Existing deploy pipeline test (reference for test structure)
- `packages/tests/integration/conftest.py` -- Integration fixtures (api_client, firestore_client, test_prefix)
- `packages/tests/test_mcp_nodes.py` -- MCP tool unit test patterns

### Requirements
- `.planning/REQUIREMENTS.md` -- Traceability table needing cleanup (D-10)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Integration test fixtures** (`packages/tests/integration/conftest.py`): api_client, firestore_client, test_prefix, sample_project_data, sample_envelope_data -- all reusable for new e2e tests
- **Existing deploy test** (`packages/tests/integration/test_api_deploy.py`): Full deploy pipeline test with 5-min timeout and SKIP_DEPLOY_TEST flag -- pattern to follow
- **MCP tool test patterns** (`packages/tests/test_mcp_nodes.py`): Mocked blueprint store, patched deps -- pattern for MCP tool unit tests

### Established Patterns
- Integration tests use `pytestmark = pytest.mark.integration` and require live GCP
- Auth bypassed via `AUTH_DISABLED=true` in test conftest
- Test cleanup via `try/finally` blocks with UUID-prefixed test data
- Deploy tests use `SKIP_DEPLOY_TEST=true` env var for fast CI

### Integration Points
- Deploy pipeline: MCP trigger_deploy -> deploy_orchestrator._run_deploy -> Cloud Build -> GCS -> Firestore
- Debug API: Insight board panels -> GET /api/debug/* -> store functions -> Firestore
- Deploy history: list_deploys query -> Firestore deploys collection (BROKEN -- D-04)

</code_context>

<specifics>
## Specific Ideas

- Both paths (MCP agent and UI human) must work for the complete deploy pipeline -- this is the core acceptance criterion
- UI must expose debug view -- the insight board IS the human's window into the pipeline
- Keep it dead simple -- minimum viable path that proves deployment works end-to-end
- Target project "My Test Project" is already provisioned and ready for testing

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-end-to-end-user-acceptance-testing-suite*
*Context gathered: 2026-03-29*
