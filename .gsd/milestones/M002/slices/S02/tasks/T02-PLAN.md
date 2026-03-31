---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T02: Implement validate_refs() and wire into validate_blueprint

Add `validate_refs()` function to `packages/core/core/validation.py` that walks RESOURCE_REFS, extracts field values from each node's config using the `get_nested()` helper from refs.py, parses `node:name.attribute` format values, looks up target nodes (by name or id in the node map), and checks the target node's type matches the FieldRef.target_type. For list fields (env_vars[].secret), iterate the list and validate each entry. Skip None/empty values (optional refs). Return list[ValidationIssue] with severity 'error'.

Wire `validate_refs()` into `validate_blueprint()` alongside existing `validate_depends_on()` call.

Add tests to test_refs.py: (1) valid refs pass with no issues, (2) ref to non-existent node produces error, (3) ref to wrong-type node produces error, (4) optional empty ref field is skipped, (5) env_var secret refs validated in list context.

IMPORTANT: The node lookup must support both id-based and name-based lookups since ref values use `node:<name>.attribute` format where `<name>` is the node name, not the UUID id. Build a name-keyed lookup for ref resolution.

## Inputs

- `packages/core/core/refs.py`
- `packages/core/core/validation.py`
- `packages/core/core/schemas/base.py`
- `packages/core/tests/test_refs.py`

## Expected Output

- `packages/core/core/validation.py`
- `packages/core/tests/test_refs.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py tests/test_validation.py -v
