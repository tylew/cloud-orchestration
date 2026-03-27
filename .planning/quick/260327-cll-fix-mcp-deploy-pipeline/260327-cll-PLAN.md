---
phase: quick
plan: 260327-cll
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/mcp/tools/blueprint.py
  - packages/mcp/tools/deploy.py
  - .env.local
  - docker-compose.yml
  - firestore.indexes.json
autonomous: true
must_haves:
  truths:
    - "validate_blueprint reconstructs Envelope from node subcollection, not get_env_blueprint"
    - "preview_terraform reconstructs Envelope from node subcollection, not get_env_blueprint"
    - "trigger_deploy reconstructs Envelope from node subcollection for validation gate"
    - "MCP server resolves DEV_TENANT_ID to yBi9vPkZ5HXNw7zyfSr7zltjojC2"
    - "Firestore composite index exists for deploys collection query"
  artifacts:
    - path: "packages/mcp/tools/blueprint.py"
      provides: "Fixed validate_blueprint and preview_terraform"
    - path: "packages/mcp/tools/deploy.py"
      provides: "Fixed trigger_deploy validation gate"
    - path: ".env.local"
      provides: "DEV_TENANT_ID and DEV_USER_EMAIL env vars"
    - path: "docker-compose.yml"
      provides: "DEV_TENANT_ID and DEV_USER_EMAIL passed to app service"
    - path: "firestore.indexes.json"
      provides: "Composite index for deploys queries"
  key_links:
    - from: "packages/mcp/tools/blueprint.py"
      to: "packages/platform/store/blueprints.py::list_nodes"
      via: "Envelope reconstruction from node dicts"
      pattern: "Envelope\\.model_validate.*nodes.*list_nodes"
    - from: "packages/mcp/tools/deploy.py"
      to: "packages/platform/store/blueprints.py::list_nodes"
      via: "Envelope reconstruction for validation gate"
      pattern: "Envelope\\.model_validate.*nodes.*list_nodes"
---

<objective>
Fix MCP tools so the full deploy pipeline works end-to-end: add node -> validate -> preview TF -> deploy.

The core bug: `validate_blueprint`, `preview_terraform`, and `trigger_deploy` all call `blueprint_store.get_env_blueprint()` which reads from a parent blueprint doc that does not exist when nodes are created individually via `save_node()`. The fix is to reconstruct an Envelope from the node subcollection using `list_nodes()`, exactly as `nodes._run_validation_and_persist` already does.

Secondary fixes: add missing env vars for MCP tenant context, add Firestore composite index for deploy queries.

Purpose: Unblock end-to-end MCP deploy pipeline testing against live project.
Output: Working validate/preview/deploy tools, correct env config, Firestore index definition.
</objective>

<execution_context>
@.planning/quick/260327-cll-fix-mcp-deploy-pipeline/260327-cll-PLAN.md
</execution_context>

<context>
@packages/mcp/tools/nodes.py (reference pattern: _run_validation_and_persist reconstructs Envelope from list_nodes)
@packages/mcp/tools/blueprint.py (files to fix)
@packages/mcp/tools/deploy.py (file to fix)
@packages/mcp/context.py (reads DEV_TENANT_ID env var)
@packages/platform/store/blueprints.py (list_nodes returns node dicts, get_env_blueprint reads parent doc)
@packages/platform/store/deploys.py (list_deploys queries project_id + created_at)

<interfaces>
<!-- Key pattern to follow — from nodes.py _run_validation_and_persist (lines 58-81) -->
```python
# This is the CORRECT pattern: reconstruct Envelope from node subcollection
all_node_dicts = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
envelope = Envelope.model_validate({
    "global": {"project_id": "validation", "region": "us-central1", "environment": "dev"},
    "nodes": all_node_dicts,
})
```

<!-- From blueprints.py -->
```python
def list_nodes(tenant_id: str, project_ref_id: str, env_name: str) -> list[dict]:
    """List all nodes for an environment."""
def get_env_blueprint(tenant_id: str, project_ref_id: str, env_name: str) -> dict | None:
    """Read blueprint for an environment, reassembling from subcollection."""
    # Returns {"env": env_name, "envelope": {...}} or None
    # PROBLEM: parent doc may not exist if nodes were created via save_node()
```

<!-- From context.py -->
```python
def get_tenant_id() -> str:
    return os.environ.get("DEV_TENANT_ID", "dev-local")
```

<!-- From deploys.py list_deploys query -->
```python
q = (ref.where("project_id", "==", project_ref_id)
     .order_by("created_at", direction=firestore.Query.DESCENDING)
     .limit(limit))
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix MCP blueprint and deploy tools to reconstruct Envelope from node subcollection</name>
  <files>packages/mcp/tools/blueprint.py, packages/mcp/tools/deploy.py</files>
  <action>
In `packages/mcp/tools/blueprint.py`, replace the `validate_blueprint` and `preview_terraform` implementations:

**validate_blueprint** (lines 94-114): Replace the `get_env_blueprint` + `Envelope.model_validate(bp["envelope"])` pattern with the same pattern used in `nodes.py::_run_validation_and_persist`:
1. Call `blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)` to get all node dicts
2. If no nodes returned, return the "not_found" error
3. Construct envelope via `Envelope.model_validate({"global": {"project_id": "validation", "region": "us-central1", "environment": env_name}, "nodes": all_node_dicts})`
4. Run validation on the envelope
5. Keep the rest of the formatting logic the same

**preview_terraform** (lines 128-144): Same fix:
1. Call `blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)` to get all node dicts
2. If no nodes returned, return the "not_found" error
3. Construct envelope via `Envelope.model_validate({"global": {"project_id": "validation", "region": "us-central1", "environment": env_name}, "nodes": all_node_dicts})`
4. Generate terraform from the envelope
5. Keep the rest of the formatting logic the same

Remove the `get_env_blueprint` import/call from both functions. `blueprint_store` is already imported for `list_nodes` in `get_blueprint`.

In `packages/mcp/tools/deploy.py`, fix the validation gate in `trigger_deploy` (lines 84-105):

Replace the `blueprint_store.get_env_blueprint` + envelope validation block with:
1. Call `blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)` — note: `blueprint_store` is already lazy-loaded via `_ensure_deps()`
2. If nodes exist, construct envelope via `Envelope.model_validate({"global": {"project_id": "validation", "region": "us-central1", "environment": env_name}, "nodes": node_dicts})`
3. Run validation and block on errors (same logic as current)
4. If no nodes, skip validation (deploy orchestrator will handle the empty blueprint case)

IMPORTANT: Do NOT change the deploy orchestrator call itself (`_run_deploy`). The deploy orchestrator uses `get_env_blueprint` internally and that's correct for its use case (it needs the full envelope with global config from the parent doc). The MCP fix is only for the pre-deploy validation gate.

Actually, looking more carefully: `_run_deploy` also calls `get_env_blueprint` and will fail if the parent doc doesn't exist. BUT the deploy orchestrator is called by both MCP and the API handler. The API handler saves the full blueprint via `save_env_blueprint` before deploying. For MCP-only workflows where nodes are added individually, the parent blueprint doc may not exist.

So ALSO: In `trigger_deploy`, after the validation gate passes and before launching `_run_deploy`, ensure a full blueprint doc exists by calling `blueprint_store.save_env_blueprint()` to persist the current nodes as a proper blueprint. This way `_run_deploy` can read it back via `get_env_blueprint`.

Add this block after the concurrency guard and before creating the deploy record:
```python
# Ensure blueprint parent doc exists for deploy orchestrator
node_dicts = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
if not node_dicts:
    return format_error("deploy_blocked", "No nodes in blueprint. Add nodes before deploying.")
blueprint_store.save_env_blueprint(tenant_id, project_ref_id, env_name, {
    "global": {"project_id": gcp_project_id, "region": region, "environment": env_name},
    "nodes": node_dicts,
})
```

Note: For this save_env_blueprint call, use the real `gcp_project_id` and `region` from the env entry (not "validation" placeholder), since this is the actual blueprint the deploy orchestrator will read.

Reuse `node_dicts` for both the validation gate and the save call to avoid double-reading from Firestore.
  </action>
  <verify>
    <automated>cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -c "
from packages.mcp.tools.blueprint import validate_blueprint, preview_terraform
from packages.mcp.tools.deploy import trigger_deploy
import inspect
src_vb = inspect.getsource(validate_blueprint)
src_pt = inspect.getsource(preview_terraform)
src_td = inspect.getsource(trigger_deploy)
assert 'get_env_blueprint' not in src_vb, 'validate_blueprint still uses get_env_blueprint'
assert 'get_env_blueprint' not in src_pt, 'preview_terraform still uses get_env_blueprint'
assert 'list_nodes' in src_vb, 'validate_blueprint missing list_nodes'
assert 'list_nodes' in src_pt, 'preview_terraform missing list_nodes'
assert 'save_env_blueprint' in src_td, 'trigger_deploy missing save_env_blueprint'
assert 'list_nodes' in src_td, 'trigger_deploy missing list_nodes'
print('All source checks passed')
"</automated>
  </verify>
  <done>validate_blueprint, preview_terraform, and trigger_deploy all reconstruct Envelope from node subcollection instead of relying on get_env_blueprint. trigger_deploy persists a full blueprint doc before launching the deploy orchestrator.</done>
</task>

<task type="auto">
  <name>Task 2: Add env vars and Firestore composite index</name>
  <files>.env.local, docker-compose.yml, firestore.indexes.json</files>
  <action>
**`.env.local`** — Append these two lines:
```
DEV_TENANT_ID=yBi9vPkZ5HXNw7zyfSr7zltjojC2
DEV_USER_EMAIL=tyler@pl4m.com
```

**`docker-compose.yml`** — In the `app` service `environment` list, add:
```yaml
- DEV_TENANT_ID=${DEV_TENANT_ID:-yBi9vPkZ5HXNw7zyfSr7zltjojC2}
- DEV_USER_EMAIL=${DEV_USER_EMAIL:-tyler@pl4m.com}
```
These go after the existing `GOOGLE_CLOUD_PROJECT` line. The `env_file: .env.local` already loads them, but explicit environment entries ensure they propagate even if env_file loading order changes.

**`firestore.indexes.json`** — Add a composite index for the deploys collection. The `list_deploys` function queries `where("project_id", "==", ...)` + `order_by("created_at", direction=DESCENDING)`. Add this index entry to the `indexes` array:
```json
{
  "collectionGroup": "deploys",
  "queryScope": "COLLECTION",
  "fields": [
    { "fieldPath": "project_id", "order": "ASCENDING" },
    { "fieldPath": "created_at", "order": "DESCENDING" }
  ]
}
```
  </action>
  <verify>
    <automated>cd /Users/fsl/Documents/GitHub/gcp-orchestration && grep -q 'DEV_TENANT_ID=yBi9vPkZ5HXNw7zyfSr7zltjojC2' .env.local && grep -q 'DEV_USER_EMAIL=tyler@pl4m.com' .env.local && grep -q 'DEV_TENANT_ID' docker-compose.yml && python -c "import json; idx=json.load(open('firestore.indexes.json')); deploys=[i for i in idx['indexes'] if i['collectionGroup']=='deploys']; assert len(deploys)==1, f'Expected 1 deploys index, got {len(deploys)}'; print('All config checks passed')"</automated>
  </verify>
  <done>DEV_TENANT_ID and DEV_USER_EMAIL set in .env.local and docker-compose.yml. Firestore composite index for deploys (project_id + created_at DESC) added to firestore.indexes.json.</done>
</task>

</tasks>

<verification>
1. Source inspection confirms no `get_env_blueprint` calls remain in blueprint.py validate/preview tools
2. Source inspection confirms `list_nodes` + `Envelope.model_validate` pattern in all three tools
3. Source inspection confirms `save_env_blueprint` call in trigger_deploy before launching orchestrator
4. Env vars present in .env.local and docker-compose.yml
5. Firestore index JSON is valid and contains deploys composite index
</verification>

<success_criteria>
- validate_blueprint works against a project with nodes added via add_node (no pre-existing blueprint parent doc)
- preview_terraform works against same project
- trigger_deploy passes validation gate and persists blueprint for deploy orchestrator
- MCP server resolves correct tenant ID (yBi9vPkZ5HXNw7zyfSr7zltjojC2) from env
- firestore.indexes.json deployable via `firebase deploy --only firestore:indexes`
</success_criteria>

<output>
After completion, create `.planning/quick/260327-cll-fix-mcp-deploy-pipeline/260327-cll-SUMMARY.md`
</output>
