---
id: T03
parent: S02
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/dag.py", "packages/core/tests/test_refs.py"]
key_decisions: ["Name-based resolution via _name_to_id dict for O(1) ref target lookup"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 206 tests pass (200 existing + 6 new), 3 xfailed. No regressions."
completed_at: 2026-03-31T08:45:53.186Z
blocker_discovered: false
---

# T03: Add _infer_ref_edges() to BlueprintDAG for auto-dependency inference from RESOURCE_REFS contract

> Add _infer_ref_edges() to BlueprintDAG for auto-dependency inference from RESOURCE_REFS contract

## What Happened
---
id: T03
parent: S02
milestone: M002
key_files:
  - packages/core/core/dag.py
  - packages/core/tests/test_refs.py
key_decisions:
  - Name-based resolution via _name_to_id dict for O(1) ref target lookup
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:45:53.186Z
blocker_discovered: false
---

# T03: Add _infer_ref_edges() to BlueprintDAG for auto-dependency inference from RESOURCE_REFS contract

**Add _infer_ref_edges() to BlueprintDAG for auto-dependency inference from RESOURCE_REFS contract**

## What Happened

Added `_infer_ref_edges()` method to BlueprintDAG that walks RESOURCE_REFS for each node, extracts populated ref field values (both scalar and list fields), resolves target node names to IDs via a new `_name_to_id` index, and adds implicit dependency edges to `self._graph`. Called automatically from `__init__` after `_build_graph()` so inferred edges are included in topological sort, cycle detection, and parallel batches. Added 6 new tests covering scalar refs, multiple refs, list refs (env_var secrets), bare values, topological ordering, and missing targets.

## Verification

All 206 tests pass (200 existing + 6 new), 3 xfailed. No regressions.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/ -v` | 0 | ✅ pass | 115500ms |


## Deviations

Fixed test data: vpc_connector needs region field; env_var type enum is 'value' not 'plain'.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/dag.py`
- `packages/core/tests/test_refs.py`


## Deviations
Fixed test data: vpc_connector needs region field; env_var type enum is 'value' not 'plain'.

## Known Issues
None.
