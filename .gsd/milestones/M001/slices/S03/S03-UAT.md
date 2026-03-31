# S03: Archive Dead Code & Minimal Test UI — UAT

**Milestone:** M001
**Written:** 2026-03-31T07:48:11.827Z

# S03: Archive Dead Code & Minimal Test UI — UAT

**Milestone:** M001
**Written:** 2026-03-31

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: The Core Explorer is a running web app — all features must be verified against live endpoints and browser rendering.

## Preconditions

- Python 3.12 available
- From `packages/core/`: `PYTHONPATH=. python -m explorer.app` starts on port 8100
- Browser available at http://localhost:8100

## Smoke Test

`curl -s http://localhost:8100/api/types | python -m json.tool | head -5` returns JSON with resource type definitions.

## Test Cases

### 1. Resource Type Palette

1. Open http://localhost:8100 in browser
2. Observe the resource palette on the left side
3. **Expected:** All 20 resource types displayed, grouped by category (Compute, Data, Messaging, Network, Security, Storage, Identity). Each category is color-coded.

### 2. Add Resources to Blueprint

1. Click a resource type (e.g., "Cloud Run") in the palette
2. Fill in the required fields in the config dialog (at minimum: `slug` and `name`)
3. Click Add/Save
4. **Expected:** Resource appears in the blueprint resource list. Repeat for 2-3 more types.

### 3. Configure Dependencies

1. Add at least two resources (e.g., Cloud Run + Cloud SQL)
2. Edit the Cloud Run resource's `depends_on` to include the Cloud SQL resource
3. **Expected:** Dependency recorded and visible in the resource configuration.

### 4. Run Validation

1. With 2+ resources in the blueprint, click Validate
2. **Expected:** Validation panel shows results — either green "valid" or a list of issues with severity (error/warning) and messages.

### 5. Generate Terraform

1. With a valid blueprint, click Generate Terraform
2. **Expected:** Terraform preview panel shows generated HCL, split by file (e.g., main.tf, variables.tf). HCL should reference the configured resources.

### 6. DAG Visualization

1. With 2+ resources including at least one dependency, click DAG
2. **Expected:** SVG visualization shows nodes positioned in columns (parallel batches). Edges drawn between dependent nodes. Nodes color-coded by category.

### 7. API Endpoints Direct

1. `curl http://localhost:8100/api/types` → JSON object with all 20 types
2. `POST /api/validate` with `{"version":"1.0","global":{"project_id":"test","region":"us-central1","environment":"dev"},"nodes":[]}` → `{"valid":true,"issues":[]}`
3. `POST /api/terraform` with same envelope → generated HCL content
4. `POST /api/dag` with same envelope → nodes and edges arrays

## Edge Cases

### Empty Blueprint Validation
1. Click Validate with no resources added
2. **Expected:** Returns valid (empty blueprints have no violations) or a warning about empty blueprints.

### Nested Config Fields
1. Add a resource with nested config (e.g., Firestore with collections)
2. Try to configure nested fields in the form
3. **Expected:** Top-level fields render as form inputs. Nested objects/arrays show a JSON text area for manual editing (known limitation).

## Failure Signals

- App fails to start on port 8100
- `/api/types` returns error or empty object
- UI shows blank page or JS errors in console
- Validation always returns empty regardless of blueprint state
- Terraform generation returns empty or error for a valid blueprint

## Not Proven By This UAT

- Dead code archival (R006) — not performed in this slice
- Full end-to-end workflow from project creation through deploy (only core package features tested)
- Nested config editing UX (known limitation — requires JSON editing)
- Performance under load or with large blueprints

## Notes for Tester

The config form only handles top-level primitive fields. For complex configs (Firestore collections, BigQuery schemas), you'll need to edit the JSON directly in the text area fallback. This is a known limitation documented in the task summary.
