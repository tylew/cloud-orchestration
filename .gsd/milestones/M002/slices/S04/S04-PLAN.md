# S04: Explorer UI — Reference Dropdowns, Naming Preview, Rename

**Goal:** Explorer UI renders ref fields as dropdowns filtered by target type, shows GCP name preview per resource, supports rename without breaking deps, and warns on immutable names.
**Demo:** After this: After this: explorer UI renders ref fields as dropdowns filtered by target type; GCP name preview shown per resource; rename works without breaking anything; immutable name warnings shown

## Tasks
- [x] **T01: Add explorer API endpoints for ref metadata, naming info, and name preview** — Enhance the explorer FastAPI backend to expose ref and naming metadata needed by the frontend.

## Steps

1. In `packages/core/explorer/app.py`, import `RESOURCE_REFS` from `core.refs` and `preview_gcp_name` from `core.registry`.
2. Enhance the existing `/api/types` endpoint to include two new fields per type:
   - `refs`: list of ref field entries from RESOURCE_REFS for that NodeType (each with `field_path`, `target_type`, `is_list`)
   - `naming`: object with `gcp_name_template`, `gcp_name_immutable` from the ComponentDefinition in REGISTRY
3. Add a `POST /api/preview-name` endpoint that accepts `{name, type, config}` and returns `{gcp_name: str}` using `preview_gcp_name()`. Import `BaseNode` from `core.schemas.base` to construct a node for the preview call.
4. Create `packages/core/tests/test_explorer_api.py` using FastAPI TestClient:
   - Test `/api/types` returns ref and naming metadata for cloud_run (has refs) and service_account (immutable)
   - Test `/api/preview-name` returns a valid preview string
   - Test `/api/preview-name` with unknown type returns appropriate response
5. Run full test suite to confirm no regressions.

## Must-Haves
- `/api/types` includes `refs` array and `naming` object per type
- `/api/preview-name` endpoint works with valid node data
- `test_explorer_api.py` passes with all assertions
- Existing test suite has no regressions
  - Estimate: 45m
  - Files: packages/core/explorer/app.py, packages/core/tests/test_explorer_api.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v && PYTHONPATH=. python -m pytest tests/ -q --ignore=tests/test_terraform_validate.py
- [x] **T02: Explorer UI now renders ref fields as filtered dropdowns, shows GCP name preview per node, displays immutable-name warnings, and supports inline rename** — Update the single-page explorer UI (vanilla JS/HTML) to consume the new API metadata for all four features.

## Steps

1. In `packages/core/explorer/static/index.html`, update the `init()` function to store the full types response (which now includes `refs` and `naming` per type).
2. **Ref dropdowns in config dialog:** In `addResource()`, after rendering normal form fields from JSON schema, check `types[type].refs` for ref fields. For each non-list ref field (where `is_list` is false), render a `<select>` dropdown instead of a text input. The dropdown options should be filtered to nodes in `blueprint.nodes` whose `type` matches the ref's `target_type`. Skip list-type ref fields (they remain in JSON editor).
3. **GCP name preview:** In `renderBlueprint()`, for each node card, compute the preview name. Call `/api/preview-name` once after render for each node and display the result below the type badge. Alternatively, fetch all previews in one pass. Show the preview as a small monospace text like `<env>-my-service`.
4. **Immutable name warning:** In `renderBlueprint()`, check `types[n.type].naming.gcp_name_immutable`. If true, add a small warning badge (e.g., yellow `⚠ name locked after deploy`) on the node card.
5. **Inline rename:** Make the node name (`<h3>`) in the node card header editable. On click, replace with an `<input>`, on blur/enter save the new name. Since depends_on uses UUIDs (from S01), renaming doesn't break deps. Update the node's `name` field in `blueprint.nodes` and re-render.
6. Test manually: run `cd packages/core && PYTHONPATH=. python -m explorer.app`, open http://localhost:8100, add a Cloud Run node, verify dropdown appears for service_account ref field, verify GCP name preview shows, verify immutable warning on Service Account type, verify rename works.

## Must-Haves
- Ref fields render as `<select>` dropdowns filtered by target type
- GCP name preview shown on each node card
- Immutable types show warning badge
- Node name is editable inline
- No JavaScript errors in console during normal use
  - Estimate: 1h
  - Files: packages/core/explorer/static/index.html
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v && test -f explorer/static/index.html && grep -q 'preview-name' explorer/static/index.html && grep -q 'gcp_name_immutable\|immutable' explorer/static/index.html
