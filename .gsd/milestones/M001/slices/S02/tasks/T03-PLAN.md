---
estimated_steps: 11
estimated_files: 4
skills_used: []
---

# T03: Add DAG contract edges and IAM inference from contracts

Extend BlueprintDAG with `contract_edges()` method. Add `infer_iam_roles_from_contract()` to iam_mappings.py. Write tests for both.

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

## Inputs

- ``packages/core/core/schemas/contracts.py``
- ``packages/core/core/dag.py``
- ``packages/core/core/iam_mappings.py``
- ``docs/specs/service-contract.md``

## Expected Output

- ``packages/core/core/dag.py``
- ``packages/core/core/iam_mappings.py``
- ``packages/core/tests/test_dag.py``
- ``packages/core/tests/test_iam_mappings.py``

## Verification

cd packages/core && python -m pytest tests/test_dag.py tests/test_iam_mappings.py tests/ -v --tb=short 2>&1 | tail -30
