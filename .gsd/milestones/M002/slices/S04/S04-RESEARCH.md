# S04 Research: Explorer UI — Reference Dropdowns, Naming Preview, Rename

## Summary

S04 is straightforward UI wiring. All backend infrastructure is complete: `RESOURCE_REFS` contract in `refs.py` (34 fields across 12 types), `resolve_gcp_name()`/`preview_gcp_name()` in `registry.py`, and UUID-based `BaseNode.id` from S01. The explorer is a single HTML file (353 lines) with a FastAPI backend (`app.py`, 5 endpoints). The work is: expose ref/naming metadata via new API endpoints, then update the frontend to render ref fields as dropdowns, show GCP name previews, support rename, and warn on immutable names.

No new libraries, no risky integrations, no architectural decisions needed.

## Recommendation

Add 2-3 new API endpoints to `explorer/app.py` to expose ref metadata and naming previews. Then update `explorer/static/index.html` to consume them. Build order: API endpoints first (testable with curl), then frontend changes. Verify by running the explorer and manually testing the four features.

## Implementation Landscape

### Key Files

- `packages/core/explorer/app.py` — FastAPI backend, needs new endpoints: `/api/refs` (return RESOURCE_REFS as JSON), `/api/naming` (return naming metadata per type), possibly enhance `/api/types` to include ref and naming info inline
- `packages/core/explorer/static/index.html` — Single-page UI (353 lines), needs: ref field dropdowns in config dialog, GCP name preview per node card, rename support (edit name without changing id), immutable name warnings
- `packages/core/core/refs.py` — `RESOURCE_REFS` dict and `FieldRef` dataclass — read-only, provides ref metadata
- `packages/core/core/registry.py` — `REGISTRY` with `gcp_name_source`, `gcp_name_template`, `gcp_name_immutable`, `resolve_gcp_name()`, `preview_gcp_name()` — read-only, provides naming metadata
- `packages/core/core/schemas/base.py` — `BaseNode` with `id` field (UUID auto-generated) — already handles rename safety since `depends_on` uses IDs

### Build Order

1. **API endpoints** — Expose ref metadata and naming info from `app.py`. This is the foundation everything else needs. Enhance `/api/types` to include `refs` (from RESOURCE_REFS) and `naming` (gcp_name_template, gcp_name_immutable) per type. Add a `/api/preview-name` POST endpoint that takes a node and returns its preview GCP name.
2. **Frontend: ref dropdowns** — In the config dialog (`addResource` and config editing), detect ref fields from the type's metadata and render them as `<select>` dropdowns filtered to nodes of the target type, instead of free-text inputs.
3. **Frontend: GCP name preview + immutable warnings** — In each node card, show the preview GCP name (call `preview_gcp_name` logic, or compute client-side from the template). Show a warning badge for immutable name types.
4. **Frontend: rename support** — Make node name editable in the card header. Since `depends_on` uses UUIDs (from S01), renaming a node's display name doesn't break anything. The UI just needs to allow inline editing of `node.name`.

### Verification Approach

- Run explorer: `cd packages/core && PYTHONPATH=. python -m explorer.app`
- Verify at http://localhost:8100:
  - Add a Cloud Run node → config dialog shows `service_account` and `vpc_access.connector` as dropdowns (filtered to SA and VPC Connector nodes)
  - Each node card shows GCP name preview (e.g., `<env>-my-service`)
  - Immutable types (Service Account, Firestore, Cloud SQL) show warning badge
  - Double-click node name to rename → deps don't break, DAG still works
- Run existing tests to confirm no regressions: `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q --ignore=tests/test_terraform_validate.py`

## Constraints

- Explorer is a single HTML file — no build system, no npm, no React. All JS is vanilla. Keep it that way.
- `preview_gcp_name()` replaces `${var.environment}` with `<env>` — can't show actual environment name since it's not known until deploy.
- Ref values in config are plain node name strings (not UUIDs) — the dropdown should set name values, matching the current ref contract.

## Common Pitfalls

- **Ref dropdowns for list fields** — `env_vars[].secret` means each env var item has a `secret` field. The config dialog currently skips arrays/objects. For list-type ref fields, the dropdown needs to be in the JSON editor or the dialog needs array-item editing. Simplest: show dropdowns only for non-list ref fields; list refs stay as JSON editing.
- **Name preview timing** — GCP name depends on config fields (e.g., `config.account_id` for SA). Preview should update as config changes, not just on add.
