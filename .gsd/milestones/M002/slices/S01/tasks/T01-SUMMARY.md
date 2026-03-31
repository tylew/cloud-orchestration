---
id: T01
parent: S01
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/schemas/base.py", "packages/core/core/dag.py", "packages/core/core/validation.py", "packages/core/tests/conftest.py", "packages/core/tests/test_dag.py", "packages/core/tests/test_validation.py"]
key_decisions: ["Deterministic UUIDs in fixtures for stable test references", "slug field removed entirely rather than deprecated"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran pytest on test_dag.py and test_validation.py (20/20 pass). Ran 5 additional test files (89/89 pass). Total 109 tests, zero failures."
completed_at: 2026-03-31T08:08:42.749Z
blocker_discovered: false
---

# T01: Added UUID id field to BaseNode with auto-generation, removed slug, switched DAG and validation to id-keyed lookups — all 109 tests pass

> Added UUID id field to BaseNode with auto-generation, removed slug, switched DAG and validation to id-keyed lookups — all 109 tests pass

## What Happened
---
id: T01
parent: S01
milestone: M002
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/dag.py
  - packages/core/core/validation.py
  - packages/core/tests/conftest.py
  - packages/core/tests/test_dag.py
  - packages/core/tests/test_validation.py
key_decisions:
  - Deterministic UUIDs in fixtures for stable test references
  - slug field removed entirely rather than deprecated
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:08:42.749Z
blocker_discovered: false
---

# T01: Added UUID id field to BaseNode with auto-generation, removed slug, switched DAG and validation to id-keyed lookups — all 109 tests pass

**Added UUID id field to BaseNode with auto-generation, removed slug, switched DAG and validation to id-keyed lookups — all 109 tests pass**

## What Happened

Added `id: str` field to BaseNode with UUID auto-generation in model validator. Removed `slug` field. Switched BlueprintDAG to id-keyed graph (node_map, build_graph, topological_sort, validate_ordering, parallel_batches). Updated validation.py: validate_parent_refs uses id_map, validate_depends_on uses id_set, added duplicate id check, renamed validate_blueprint_by_slug to validate_blueprint_by_id, switched reconstruct_collection_tree to id-based lookup. Updated all test fixtures with deterministic UUIDs and id-based depends_on.

## Verification

Ran pytest on test_dag.py and test_validation.py (20/20 pass). Ran 5 additional test files (89/89 pass). Total 109 tests, zero failures.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -v` | 0 | ✅ pass | 50ms |
| 2 | `PYTHONPATH=. python -m pytest tests/test_registry.py tests/test_iam_mappings.py tests/test_env_vars.py tests/test_cloud_dns.py tests/test_auto_provision.py -v` | 0 | ✅ pass | 150ms |


## Deviations

Auto-provision tests also validated beyond plan scope to catch collateral breakage.

## Known Issues

test_terraform.py and test_terraform_validate.py not yet run — likely need id-based updates in downstream tasks.

## Files Created/Modified

- `packages/core/core/schemas/base.py`
- `packages/core/core/dag.py`
- `packages/core/core/validation.py`
- `packages/core/tests/conftest.py`
- `packages/core/tests/test_dag.py`
- `packages/core/tests/test_validation.py`


## Deviations
Auto-provision tests also validated beyond plan scope to catch collateral breakage.

## Known Issues
test_terraform.py and test_terraform_validate.py not yet run — likely need id-based updates in downstream tasks.
