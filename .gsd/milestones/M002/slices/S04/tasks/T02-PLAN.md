---
estimated_steps: 14
estimated_files: 1
skills_used: []
---

# T02: Update explorer frontend with ref dropdowns, GCP name preview, rename, and immutable warnings

Update the single-page explorer UI (vanilla JS/HTML) to consume the new API metadata for all four features.

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

## Inputs

- `packages/core/explorer/static/index.html`
- `packages/core/explorer/app.py`

## Expected Output

- `packages/core/explorer/static/index.html`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v && test -f explorer/static/index.html && grep -q 'preview-name' explorer/static/index.html && grep -q 'gcp_name_immutable\|immutable' explorer/static/index.html
