---
estimated_steps: 38
estimated_files: 6
skills_used: []
---

# T01: Add UUID id to BaseNode, update fixtures, DAG, and validation to use id-based keying

Foundation task: add `id` field to BaseNode with auto-generation, remove `slug`, update conftest `_node()` helper to generate deterministic UUIDs, switch BlueprintDAG from name-keyed to id-keyed graph, switch validation lookups from name/slug to id. This is the widest change — everything downstream depends on nodes having `id`.

## Steps

1. Edit `packages/core/core/schemas/base.py`:
   - Add `id: str = ""` field to BaseNode
   - In `resolve_config_and_validate` model_validator, add: `if not self.id: self.id = str(uuid.uuid4())` (import uuid at top)
   - Remove `slug: str = ""` field
   - Keep `name` validation (kebab-case) since name is still used for GCP resource names

2. Edit `packages/core/tests/conftest.py`:
   - Update `_node()` helper to accept `id` param, auto-generate `uuid.uuid4()` if not provided
   - Store generated IDs so tests can reference them in `depends_on`
   - Update ALL fixture `depends_on` values from name strings to ID references. Pattern: generate IDs at fixture level, pass to `_node()`, use same IDs in `depends_on` lists
   - Remove any `slug` references

3. Edit `packages/core/core/dag.py`:
   - Change `_node_map` to key by `node.id` (primary). Add `node.name` as secondary key for backward compat during transition
   - Change `_build_graph` to use `node.id` as graph keys instead of `node.name`
   - `topological_sort` returns nodes looked up by id
   - `validate_ordering` checks deps against id set
   - `parallel_batches` uses id keys

4. Edit `packages/core/core/validation.py`:
   - Replace all `slug_map`, `slug_set`, `name_set` lookups with `id_map`, `id_set`
   - `validate_depends_on` checks deps against id set
   - `validate_blueprint_by_slug` → rename to `validate_blueprint_by_id`, key results by `node.id`
   - Child-parent validation: switch from slug-based parent refs to id-based
   - Duplicate check: keep name uniqueness check but also add id uniqueness check

5. Update test files `packages/core/tests/test_dag.py` and `packages/core/tests/test_validation.py`:
   - Ensure all test envelope data uses id-based depends_on
   - Fix any assertions that reference node.slug or name-keyed results

6. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -v` — all pass

## Must-Haves

- BaseNode.id auto-generates UUID when missing (backward compat)
- slug field removed
- DAG indexes by id
- Validation uses id for all lookups
- test_dag.py and test_validation.py pass

## Negative Tests

- Envelope parsed without any `id` fields → every node gets a unique auto-generated UUID
- Duplicate node ids rejected by validation
- depends_on referencing non-existent id caught by DAG validation

## Inputs

- ``packages/core/core/schemas/base.py` — current BaseNode with slug, no id`
- ``packages/core/core/dag.py` — name-keyed DAG`
- ``packages/core/core/validation.py` — slug/name-keyed validation`
- ``packages/core/tests/conftest.py` — _node() helper without id support`
- ``packages/core/tests/test_dag.py` — name-based depends_on in tests`
- ``packages/core/tests/test_validation.py` — slug-based validation tests`

## Expected Output

- ``packages/core/core/schemas/base.py` — BaseNode with id field, auto-gen, no slug`
- ``packages/core/core/dag.py` — id-keyed DAG`
- ``packages/core/core/validation.py` — id-keyed validation, validate_blueprint_by_id`
- ``packages/core/tests/conftest.py` — _node() with id generation, id-based depends_on`
- ``packages/core/tests/test_dag.py` — updated for id-based depends_on`
- ``packages/core/tests/test_validation.py` — updated for id-based lookups`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -v
