---
estimated_steps: 17
estimated_files: 2
skills_used: []
---

# T01: Add explorer API endpoints for ref metadata, naming info, and name preview

Enhance the explorer FastAPI backend to expose ref and naming metadata needed by the frontend.

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

## Inputs

- `packages/core/explorer/app.py`
- `packages/core/core/refs.py`
- `packages/core/core/registry.py`
- `packages/core/core/schemas/base.py`

## Expected Output

- `packages/core/explorer/app.py`
- `packages/core/tests/test_explorer_api.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v && PYTHONPATH=. python -m pytest tests/ -q --ignore=tests/test_terraform_validate.py
