---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T03: Add auto-dependency inference from ref fields to BlueprintDAG

Add `infer_ref_edges()` method to BlueprintDAG in `packages/core/core/dag.py` that walks RESOURCE_REFS for each node, extracts populated ref field values, resolves target node names to node ids, and adds implicit edges to `self._graph`. Call this from `__init__` after `_build_graph()` so the inferred edges are included in topological sort, cycle detection, and parallel batches.

The method must: (1) import RESOURCE_REFS and get_nested from refs.py, (2) for each node, iterate its FieldRef entries, (3) parse `node:name.attribute` values to extract target name, (4) look up target node by name to get its id, (5) add edge: graph[node.id].add(target.id). Skip refs where the target isn't found (already caught by validation).

Add tests to test_refs.py: (1) Cloud Run with `service_account: 'node:my-sa.email'` auto-depends on the SA node, (2) multiple refs create multiple edges, (3) bare non-ref values don't create edges, (4) env_var secret refs create edges to secret_manager nodes.

Run full test suite to confirm no regressions: all 155+ existing tests plus new tests pass.

## Inputs

- `packages/core/core/dag.py`
- `packages/core/core/refs.py`
- `packages/core/tests/test_refs.py`
- `packages/core/tests/conftest.py`

## Expected Output

- `packages/core/core/dag.py`
- `packages/core/tests/test_refs.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/ -v
