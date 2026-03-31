---
estimated_steps: 20
estimated_files: 8
skills_used: []
---

# T03: Remove config-level ID fields and fix all test fixtures

## Why
With templates now using gcp_name from the registry, config-level ID fields (account_id, dataset_id, instance_id, database_id) are redundant. Removing them completes the abstraction. Test fixtures that provide these fields must be updated.

## Steps
1. Remove config ID fields from schemas:
   - `packages/core/core/schemas/configs/service_account.py`: Remove `account_id` field and its `validate_account_id` validator. Keep `display_name`, `description`, `disabled`, `roles`.
   - `packages/core/core/schemas/configs/bigquery.py`: Remove `dataset_id` field. Other fields stay.
   - `packages/core/core/schemas/configs/bigtable.py`: Remove `instance_id` field. Other fields stay.
   - `packages/core/core/schemas/configs/firestore.py`: Remove `database_id` field. Other fields stay.
2. Update test fixtures in `packages/core/tests/conftest.py`:
   - Remove `account_id` from service_account node configs (currently `{"account_id": "my-sa"}`)
   - Remove `dataset_id` from bigquery node configs
   - Remove `instance_id` from bigtable node configs  
   - Remove `database_id` from firestore node configs
3. Search for any other test files referencing these removed fields and update them:
   - `rg 'account_id|dataset_id|instance_id|database_id' packages/core/tests/`
4. Run the full test suite including terraform validate tests
5. Also check `packages/api/` and `packages/platform/` for references to removed fields — these are read-path only and may need updates if they construct nodes

## Constraints
- bigquery.py `dataset_id` is a required field (no default) — removing it means BQ config no longer requires this. Existing blueprints in Firestore that have dataset_id will pass through Pydantic's `extra='allow'` on BaseNode but the config model may reject unknown fields depending on its settings. Check if BQ config has `extra='allow'` or not — if not, old payloads with dataset_id will fail validation. May need to add `extra='ignore'` temporarily.
- bigtable.py `instance_id` is also required — same concern.

## Inputs

- ``packages/core/core/schemas/configs/service_account.py``
- ``packages/core/core/schemas/configs/bigquery.py``
- ``packages/core/core/schemas/configs/bigtable.py``
- ``packages/core/core/schemas/configs/firestore.py``
- ``packages/core/tests/conftest.py``

## Expected Output

- ``packages/core/core/schemas/configs/service_account.py``
- ``packages/core/core/schemas/configs/bigquery.py``
- ``packages/core/core/schemas/configs/bigtable.py``
- ``packages/core/core/schemas/configs/firestore.py``
- ``packages/core/tests/conftest.py``

## Verification

cd packages/core && python -m pytest tests/ -x -v
