# S01: Resource Identity — UUID Foundation — UAT

**Milestone:** M002
**Written:** 2026-03-31T08:31:46.633Z

# S01: Resource Identity — UUID Foundation — UAT

**Milestone:** M002
**Written:** 2026-03-31

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All changes are in core library code validated by 155 automated tests including terraform validate integration tests

## Preconditions

- Working directory: `packages/core/`
- Python 3.12 with PYTHONPATH=. set
- Terraform CLI available (for terraform validate tests)

## Smoke Test

Run `cd packages/core && PYTHONPATH=. python -m pytest tests/ -v` — expect 152 passed, 3 xfailed.

## Test Cases

### 1. UUID Auto-Generation on BaseNode

1. Parse an Envelope JSON with nodes that have no `id` field
2. Access `node.id` on each parsed node
3. **Expected:** Every node has a non-empty UUID string assigned automatically

### 2. Deterministic UUID in Fixtures

1. Run `pytest tests/test_dag.py -v`
2. **Expected:** All DAG tests pass using id-based depends_on references

### 3. TF Resource Labels Use Sanitized UUID

1. Run `pytest tests/test_terraform_validate.py -v`
2. Inspect generated HCL for any node
3. **Expected:** Resource labels match pattern `n_[0-9a-f_]+` (no dashes, no leading digits). GCP resource names still use human-readable node.name.

### 4. Slug Field Removed

1. Run `rg -c slug packages/core/core/schemas/base.py`
2. **Expected:** Exit code 1 (no matches found)

### 5. Validation Uses ID-Based Lookups

1. Run `pytest tests/test_validation.py -v`
2. **Expected:** All validation tests pass, including duplicate id detection and id-based depends_on validation

## Edge Cases

### Envelope Without Any ID Fields (Backward Compat)

1. Create an Envelope from JSON where no node has an `id` field
2. Parse it through Pydantic
3. **Expected:** Every node gets a unique auto-generated UUID; no validation errors

### Duplicate Node IDs

1. Create an Envelope with two nodes sharing the same `id`
2. Run validation
3. **Expected:** Validation produces an error about duplicate IDs

### depends_on Referencing Non-Existent ID

1. Create a node with `depends_on: ["nonexistent-uuid"]`
2. Run DAG validation
3. **Expected:** Validation catches the broken reference

## Failure Signals

- Any test in the 155-test suite failing
- `slug` appearing in base.py
- TF resource labels containing dashes or starting with digits
- Nodes missing auto-generated IDs after parsing

## Not Proven By This UAT

- API handler compatibility (packages/api/ callers of renamed function)
- Frontend TypeScript type updates
- Live deployment with real GCP resources

## Notes for Tester

The 3 xfailed tests are pre-existing (annotations dotted keys, cloud_sql authorized networks, vpc_connector) — not related to this slice.
