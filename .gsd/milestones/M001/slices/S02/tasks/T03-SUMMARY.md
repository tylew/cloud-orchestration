---
id: T03
parent: S02
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/core/dag.py", "packages/core/core/iam_mappings.py", "packages/core/tests/test_dag.py", "packages/core/tests/test_iam_mappings.py"]
key_decisions: ["Contract access levels mapped to IAM actions via _ACCESS_TO_ACTION dict; read_write maps to Write (subsumes Read)", "Event directions mapped: publish→Emit, subscribe→Read, enqueue→Enqueue"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran pytest on test_dag.py and test_iam_mappings.py (46 passed), then full suite (193 passed, 3 xfailed). All new contract_edges and infer_iam_roles_from_contract tests pass."
completed_at: 2026-03-31T06:46:59.442Z
blocker_discovered: false
---

# T03: Add DAG contract_edges() method and infer_iam_roles_from_contract() with 9 new tests

> Add DAG contract_edges() method and infer_iam_roles_from_contract() with 9 new tests

## What Happened
---
id: T03
parent: S02
milestone: M001
key_files:
  - packages/core/core/dag.py
  - packages/core/core/iam_mappings.py
  - packages/core/tests/test_dag.py
  - packages/core/tests/test_iam_mappings.py
key_decisions:
  - Contract access levels mapped to IAM actions via _ACCESS_TO_ACTION dict; read_write maps to Write (subsumes Read)
  - Event directions mapped: publish→Emit, subscribe→Read, enqueue→Enqueue
duration: ""
verification_result: passed
completed_at: 2026-03-31T06:46:59.443Z
blocker_discovered: false
---

# T03: Add DAG contract_edges() method and infer_iam_roles_from_contract() with 9 new tests

**Add DAG contract_edges() method and infer_iam_roles_from_contract() with 9 new tests**

## What Happened

Added contract_edges() to BlueprintDAG that extracts typed dependency edges from ServiceContract refs on compute nodes. Added infer_iam_roles_from_contract() to iam_mappings.py that maps contract access levels (read/write/read_write) and event directions (publish/subscribe/enqueue) to GCP IAM roles via the existing IAM_ROLE_MAP. Wrote 3 DAG tests and 6 IAM inference tests. All 193 tests pass with no regressions.

## Verification

Ran pytest on test_dag.py and test_iam_mappings.py (46 passed), then full suite (193 passed, 3 xfailed). All new contract_edges and infer_iam_roles_from_contract tests pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && python -m pytest tests/test_dag.py tests/test_iam_mappings.py -v --tb=short` | 0 | ✅ pass | 50ms |
| 2 | `cd packages/core && python -m pytest tests/ -v --tb=short` | 0 | ✅ pass | 114500ms |


## Deviations

BigQuery test required dataset_id config field — adapted _make_node helper to accept optional config dict.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/dag.py`
- `packages/core/core/iam_mappings.py`
- `packages/core/tests/test_dag.py`
- `packages/core/tests/test_iam_mappings.py`


## Deviations
BigQuery test required dataset_id config field — adapted _make_node helper to accept optional config dict.

## Known Issues
None.
