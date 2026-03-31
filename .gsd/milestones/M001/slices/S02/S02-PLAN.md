# S02: Deep DAG — Service Contract Model

**Goal:** Compute nodes define service contracts with typed resource refs; contracts validated against blueprint; DAG surfaces contract edges alongside infra deps; IAM roles inferred from contracts.
**Demo:** After this: After this: compute nodes define service contracts with typed resource refs; contracts validated against blueprint; DAG surfaces contract edges alongside infra deps

## Tasks
- [x] **T01: Define ServiceContract Pydantic models and wire into all three compute configs** — Create the ServiceContract Pydantic model hierarchy (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract) in a new `contracts.py` module. Add `contract: ServiceContract | None = None` field to CloudRunConfig, CloudRunJobConfig, and CloudFunctionConfig. Write unit tests proving models serialize/deserialize correctly and blueprints with contracts parse without error.

Steps:
1. Create `packages/core/core/schemas/contracts.py` with all 6 models per spec (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract). Use `Literal['read', 'write', 'read_write']` for access types. `Literal['publish', 'subscribe', 'enqueue']` for EventRef direction.
2. Add `contract: ServiceContract | None = None` to CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig. Import from contracts.py.
3. Create `packages/core/tests/test_contracts.py` with tests: model instantiation with all fields, JSON round-trip, optional fields default correctly, a full Envelope with a compute node + contract parses via `resolve_config_and_validate`.
4. Run full test suite to confirm no regressions.

Constraints:
- contracts.py must NOT import from configs/ (avoid circular imports — only validation code imports both)
- DataRef extends ResourceRef with collections/tables/fields lists
- All ref models share `node: str` and `description: str = ''`
  - Estimate: 45m
  - Files: packages/core/core/schemas/contracts.py, packages/core/core/schemas/configs/cloud_run.py, packages/core/core/schemas/configs/cloud_run_job.py, packages/core/core/schemas/configs/cloud_function.py, packages/core/tests/test_contracts.py
  - Verify: cd packages/core && python -m pytest tests/test_contracts.py tests/ -v --tb=short 2>&1 | tail -20
- [x] **T02: Implement contract validation with cross-schema field resolution and 15 comprehensive tests** — Add `validate_contracts()` to validation.py implementing all spec validation rules. Wire it into `validate_blueprint()`. Write comprehensive tests covering positive and negative cases.

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
  - Estimate: 1h
  - Files: packages/core/core/validation.py, packages/core/tests/test_contract_validation.py
  - Verify: cd packages/core && python -m pytest tests/test_contract_validation.py tests/test_validation.py -v --tb=short 2>&1 | tail -30
- [x] **T03: Add DAG contract_edges() method and infer_iam_roles_from_contract() with 9 new tests** — Extend BlueprintDAG with `contract_edges()` method. Add `infer_iam_roles_from_contract()` to iam_mappings.py. Write tests for both.

Steps:
1. In `packages/core/core/dag.py`, add `contract_edges()` method to BlueprintDAG. Iterate all nodes, check if node has a resolved config with a `contract` attribute (use `hasattr` or check type). For each ref in contract.data/secrets/events/invocations, yield `(source_node_name, target_node_name, access_type)` tuples. Access type: DataRef uses ref.access, SecretRef uses 'read', EventRef uses ref.direction, InvokeRef uses 'invoke'.
2. In `packages/core/core/iam_mappings.py`, add `infer_iam_roles_from_contract(contract: ServiceContract, node_map: dict[str, BaseNode]) -> set[str]`. For each DataRef, look up target node type, map (access, node_type) to IAM role using IAM_ROLE_MAP (map 'read' to 'Read', 'write'/'read_write' to 'Write'). For SecretRef, add secretAccessor. For EventRef, map direction to role. For InvokeRef, map target type to invoker role.
3. Extend `packages/core/tests/test_dag.py` with contract_edges tests: blueprint with contract produces correct edges, no contract produces empty edges.
4. Extend `packages/core/tests/test_iam_mappings.py` with infer_iam_roles_from_contract tests: DataRef→firestore infers datastore.user, DataRef→bigquery read infers dataViewer, SecretRef infers secretAccessor, EventRef publish infers publisher, InvokeRef→cloud_run infers run.invoker.
5. Run full test suite.

Constraints:
- Import ServiceContract from contracts.py in both dag.py and iam_mappings.py
- contract_edges() returns list[tuple[str, str, str]] — separate from depends_on edges
- For read_write access in IAM, infer the write role (which subsumes read for most GCP services)
  - Estimate: 45m
  - Files: packages/core/core/dag.py, packages/core/core/iam_mappings.py, packages/core/tests/test_dag.py, packages/core/tests/test_iam_mappings.py
  - Verify: cd packages/core && python -m pytest tests/test_dag.py tests/test_iam_mappings.py tests/ -v --tb=short 2>&1 | tail -30
