# S02: Deep DAG — Service Contract Model — UAT

**Milestone:** M001
**Written:** 2026-03-31T06:51:28.119Z

# S02: Deep DAG — Service Contract Model — UAT

**Milestone:** M001
**Written:** 2026-03-31

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All deliverables are Pydantic models, validation functions, and DAG methods — fully testable via unit tests without runtime

## Preconditions

- Python 3.12+ installed
- Working directory: `packages/core/`
- Dependencies installed: `pip install -e ".[dev]"`

## Smoke Test

```bash
cd packages/core && python -m pytest tests/test_contracts.py tests/test_contract_validation.py tests/test_dag.py tests/test_iam_mappings.py -q
```
Expected: 41 tests pass.

## Test Cases

### 1. Contract models serialize and deserialize

1. Run `python -m pytest tests/test_contracts.py -v`
2. **Expected:** 17 tests pass — models instantiate, JSON round-trip works, optional fields default correctly, Envelope with contract parses for all compute types

### 2. Contract validation catches invalid references

1. Run `python -m pytest tests/test_contract_validation.py -v`
2. **Expected:** 15 tests pass — valid contracts pass, refs to nonexistent nodes error, DataRef to compute type errors, SecretRef to non-secret errors, EventRef to non-messaging errors, InvokeRef to data node errors, nonexistent Firestore collections/BigQuery tables/fields error, template paths accepted

### 3. DAG surfaces contract edges

1. Run `python -m pytest tests/test_dag.py -k contract -v`
2. **Expected:** contract_edges returns typed tuples (source, target, access_type) for blueprints with contracts; empty list for no contracts

### 4. IAM roles inferred from contracts

1. Run `python -m pytest tests/test_iam_mappings.py -k infer -v`
2. **Expected:** DataRef→firestore infers datastore.user, DataRef→bigquery read infers dataViewer, SecretRef infers secretAccessor, EventRef publish infers publisher, InvokeRef→cloud_run infers run.invoker

### 5. Full suite regression

1. Run `python -m pytest tests/ --ignore=tests/test_terraform.py --ignore=tests/test_terraform_validate.py -q`
2. **Expected:** 150 tests pass, no regressions from pre-S02 baseline

## Edge Cases

### Template paths in Firestore collections

1. Create a DataRef with collection path `users/{{user_id}}/orders`
2. Run contract validation against a Firestore node that has `users` collection
3. **Expected:** Validation passes — template segments stripped before matching

### Backward compatibility — no contract

1. Create a compute node (CloudRun) with no `contract` field
2. Parse through Envelope and validate
3. **Expected:** No errors — contract defaults to None, validation skips it

## Failure Signals

- Any test in test_contracts.py or test_contract_validation.py failing
- Import errors from contracts.py (circular import with configs/)
- contract_edges() returning infrastructure edges instead of only contract edges

## Not Proven By This UAT

- Runtime API integration (contracts exposed via REST endpoints)
- UI rendering of contract edges in the DAG viewer
- GCS bucket prefix validation in DataRef
- InvokeRef API contract compatibility checking

## Notes for Tester

- Full test suite with terraform tests takes ~2 minutes. Use `--ignore=tests/test_terraform.py --ignore=tests/test_terraform_validate.py` for fast feedback.
- The 3 xfailed tests in the full suite are pre-existing and unrelated to S02.
