# S04: Explorer UI — Reference Dropdowns, Naming Preview, Rename — UAT

**Milestone:** M002
**Written:** 2026-03-31T09:14:07.897Z

# S04: Explorer UI — Reference Dropdowns, Naming Preview, Rename — UAT

**Milestone:** M002
**Written:** 2026-03-31

## UAT Type

- UAT mode: mixed (artifact-driven API tests + manual UI verification)
- Why this mode is sufficient: API endpoints are fully tested by pytest; UI features require visual/interactive confirmation

## Preconditions

- Python 3.12+ with packages/core dependencies installed
- Run: `cd packages/core && PYTHONPATH=. python -m explorer.app` (starts on http://localhost:8100)

## Smoke Test

Open http://localhost:8100, add a Cloud Run node → verify a GCP name preview appears on the card and service_account ref field shows as a dropdown.

## Test Cases

### 1. Ref dropdown renders for Cloud Run service_account field

1. Open http://localhost:8100
2. Add a Service Account node named "my-sa"
3. Add a Cloud Run node named "my-service"
4. Click "Edit Config" on the Cloud Run node
5. **Expected:** `service_account` field renders as a `<select>` dropdown with "my-sa" as an option

### 2. GCP name preview shown on node cards

1. Add a Cloud Run node named "api-server"
2. Observe the node card
3. **Expected:** A monospace preview like `dev-api-server` appears below the type badge

### 3. Immutable name warning on Service Account

1. Add a Service Account node
2. Observe the node card
3. **Expected:** A yellow "⚠ name locked after deploy" warning badge is visible

### 4. Inline rename works without breaking deps

1. Add two nodes: Cloud SQL "my-db" and Cloud Run "my-app" (with my-db as dependency)
2. Click on "my-db" name text in the card header
3. Change name to "renamed-db", press Enter
4. **Expected:** Node name updates to "renamed-db"; depends_on still references the UUID (no breakage)

### 5. API: /api/types includes refs and naming

1. Run: `curl http://localhost:8100/api/types | jq '.cloud_run.refs'`
2. **Expected:** Array includes entry with `field_path` containing "service_account" and `target_type` "service_account"
3. Run: `curl http://localhost:8100/api/types | jq '.service_account.naming'`
4. **Expected:** Object with `gcp_name_immutable: true`

### 6. API: /api/preview-name

1. Run: `curl -X POST http://localhost:8100/api/preview-name -H 'Content-Type: application/json' -d '{"name":"my-svc","type":"cloud_run","config":{}}'`
2. **Expected:** Response contains `gcp_name` field with a formatted name string

## Edge Cases

### Unknown type returns 422

1. POST to `/api/preview-name` with `{"name":"x","type":"nonexistent","config":{}}`
2. **Expected:** 422 response

### Dropdown empty when no matching nodes exist

1. Add a Cloud Run node with no Service Account nodes in blueprint
2. Edit config
3. **Expected:** service_account dropdown is empty (no options)

## Failure Signals

- JavaScript console errors when rendering node cards
- Missing dropdown for known ref fields (e.g., service_account on Cloud Run)
- No GCP name preview appearing on any node card
- pytest test_explorer_api.py failures

## Not Proven By This UAT

- List-type ref fields (multi-select) — deferred, still rendered in JSON editor
- Performance under large blueprints (50+ nodes)
- Production deployment of explorer

## Notes for Tester

The explorer is a dev-only tool (not the main app UI). It runs standalone on port 8100. The name preview makes async fetch calls — give it a moment to appear after adding nodes.
