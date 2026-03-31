# S02: Reference Contract — Type-Safe Cross-Resource Wiring — UAT

**Milestone:** M002
**Written:** 2026-03-31T08:49:36.823Z

# S02: Reference Contract — Type-Safe Cross-Resource Wiring — UAT

**Milestone:** M002
**Written:** 2026-03-31

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All behavior is exercised through pytest — no runtime server needed

## Preconditions

- Working directory: `packages/core`
- Python environment with dependencies installed
- PYTHONPATH=. set for imports

## Smoke Test

```bash
cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py -v --tb=short
```
All 54 tests pass — confirms contract, validation, and DAG inference work.

## Test Cases

### 1. Contract completeness — all ref-bearing node types declared

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestResourceRefsContract -v`
2. **Expected:** Tests confirm CLOUD_RUN, CLOUD_FUNCTION, CLOUD_RUN_JOB, SUBNET, VPC_CONNECTOR, CLOUD_SQL, EXTERNAL_LB, PUBSUB_SUBSCRIPTION, PUBSUB_TOPIC, CLOUD_TASK_QUEUE, GCS_BUCKET all present in RESOURCE_REFS

### 2. Dot-path validation — every FieldRef.field resolves on its config model

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestFieldPathsResolve -v`
2. **Expected:** Every dot-path in every FieldRef resolves to a real field on the corresponding Pydantic config model

### 3. validate_refs() catches missing target node

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestValidateRefs::test_ref_to_nonexistent_node -v`
2. **Expected:** ValidationIssue with severity 'error' for ref pointing to non-existent node

### 4. validate_refs() catches wrong-type target

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestValidateRefs::test_ref_to_wrong_type -v`
2. **Expected:** ValidationIssue with severity 'error' when ref points to node of wrong type

### 5. DAG auto-infers edges from refs

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestInferRefEdges -v`
2. **Expected:** BlueprintDAG.topological_sort() orders ref targets before referencing nodes without explicit depends_on

### 6. Full test suite — no regressions

1. Run `PYTHONPATH=. python -m pytest tests/ -v`
2. **Expected:** 206 passed, 3 xfailed, 0 failures

## Edge Cases

### Empty/optional ref fields skipped

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestValidateRefs::test_optional_empty_ref -v`
2. **Expected:** No validation issues for None/empty ref fields

### List field refs (env_vars secrets)

1. Run `PYTHONPATH=. python -m pytest tests/test_refs.py::TestValidateRefs::test_env_var_secret_refs -v`
2. **Expected:** Each secret ref in env_vars list validated individually

## Failure Signals

- Any test failure in test_refs.py indicates broken contract or validation logic
- Regressions in test_dag.py or test_validation.py indicate wiring issues

## Not Proven By This UAT

- Terraform generator consuming tf_attribute from refs (deferred)
- UUID-based ref resolution (currently name-based)
- UI rendering of ref fields as dropdowns (S04)

## Notes for Tester

- test_terraform_validate.py takes ~100s due to real terraform binary calls — be patient
- Ref values in config are plain slugs like \"my-sa\", not node:name.attribute format
