---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T03: Full regression verification

Run the full core test suite, all terraform validate tests, and all other package tests. Confirm zero regressions.

## Inputs

- None specified.

## Expected Output

- `All tests green across all packages`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/ -v && cd ../.. && python -m pytest packages/platform/tests/ packages/api/tests/ packages/mcp/tests/ -q --ignore=packages/platform/tests/integration
