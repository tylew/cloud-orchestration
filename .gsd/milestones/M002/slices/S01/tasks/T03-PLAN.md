---
estimated_steps: 12
estimated_files: 5
skills_used: []
---

# T03: Full regression — run entire test suite and fix remaining breakage

Run the full 155-test suite, fix any tests broken by the id migration that weren't caught in T01/T02, and verify backward compatibility (envelopes without id auto-migrate).

## Steps

1. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/ -v` — identify any failures
2. Fix any remaining test files that reference `slug` or use name-based depends_on
3. Verify backward compat: write a quick inline test or assertion that an Envelope parsed from JSON without `id` fields gets auto-assigned UUIDs on every node
4. Verify that `validate_blueprint_by_id` (renamed from `validate_blueprint_by_slug`) works correctly with id-keyed results
5. Check for any callers of `validate_blueprint_by_slug` in `packages/api/` or `packages/platform/` and update the import/call if needed
6. Run full suite again — all 155 tests green

## Must-Haves

- Full test suite passes (155 tests)
- No references to `slug` remain in core package (except possibly in migration comments)
- Backward compat proven: envelope without id → auto-assigns UUIDs

## Inputs

- ``packages/core/core/schemas/base.py` — BaseNode with id, no slug from T01`
- ``packages/core/core/dag.py` — id-keyed DAG from T01`
- ``packages/core/core/validation.py` — id-keyed validation from T01`
- ``packages/core/core/terraform/generator.py` — id-based generator from T02`
- ``packages/core/core/terraform/templates/*.tf.j2` — updated templates from T02`
- ``packages/core/tests/conftest.py` — id-based fixtures from T01`

## Expected Output

- ``packages/core/tests/test_terraform_validate.py` — all tests passing with id-based nodes`
- ``packages/core/tests/test_dag.py` — fully passing`
- ``packages/core/tests/test_validation.py` — fully passing`
- ``packages/core/core/validation.py` — no slug references remain`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/ -v && rg -c 'slug' packages/core/core/schemas/base.py; test $? -ne 0
