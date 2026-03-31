---
estimated_steps: 1
estimated_files: 2
skills_used: []
---

# T06: Full regression + audit report

Run entire test suite to confirm no regressions. Test backward compatibility by validating existing test blueprints against updated schemas. Write audit report summarizing what was found and changed per type.

## Inputs

- `All updated schemas and templates from T01-T05`

## Expected Output

- `All tests passing`
- `docs/audit-report-s01.md with per-type gap summary`

## Verification

pytest packages/tests/ -v --tb=short
