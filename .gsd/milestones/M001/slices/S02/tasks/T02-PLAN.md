---
estimated_steps: 15
estimated_files: 2
skills_used: []
---

# T02: Implement contract validation with cross-schema field resolution

Add `validate_contracts()` to validation.py implementing all spec validation rules. Wire it into `validate_blueprint()`. Write comprehensive tests covering positive and negative cases.

Steps:
1. In `packages/core/core/validation.py`, add `validate_contracts(envelope: Envelope) -> list[ValidationIssue]` function. Build a node_map by name. For each compute node with a contract, validate:
   - DataRef: node exists, node type is storage (firestore/cloud_sql/bigquery/bigtable/gcs_bucket). If collections specified and target is Firestore, each path must exist in target's collection definitions (strip `{{...}}` template segments from paths before matching). If tables specified and target is Cloud SQL/BigQuery, each table must exist. If fields specified, resolve `collection.field` or `table.field` against target schema.
   - SecretRef: node exists, type is secret_manager.
   - EventRef: node exists, type is pubsub_topic or cloud_task_queue.
   - InvokeRef: node exists, type is a COMPUTE_TYPE.
2. Call `validate_contracts(envelope)` from `validate_blueprint()` (add `issues.extend(validate_contracts(envelope))` after existing cross-node checks).
3. Create `packages/core/tests/test_contract_validation.py` with tests: valid contract passes, ref to nonexistent node errors, DataRef to compute type errors, SecretRef to non-secret errors, EventRef to non-messaging errors, InvokeRef to data node errors, nonexistent Firestore collection errors, nonexistent BigQuery table errors, nonexistent field errors, template path `{{user_id}}` in collection path accepted.
4. Run full test suite.

Constraints:
- Import ServiceContract and ref types from contracts.py
- Use COMPUTE_TYPES from enums.py for InvokeRef validation
- Firestore collection paths may include `{{...}}` template segments — strip these before matching against collection definitions
- Field resolution: split on `.` — first segment is collection/table name, second is field name. Look up in target config's collections[].fields[] or tables[].columns[]

## Inputs

- ``packages/core/core/schemas/contracts.py``
- ``packages/core/core/validation.py``
- ``packages/core/core/schemas/configs/firestore.py``
- ``packages/core/core/schemas/configs/bigquery.py``
- ``packages/core/core/schemas/configs/cloud_sql.py``
- ``docs/specs/service-contract.md``

## Expected Output

- ``packages/core/core/validation.py``
- ``packages/core/tests/test_contract_validation.py``

## Verification

cd packages/core && python -m pytest tests/test_contract_validation.py tests/test_validation.py -v --tb=short 2>&1 | tail -30
