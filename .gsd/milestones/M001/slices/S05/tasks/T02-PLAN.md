---
estimated_steps: 2
estimated_files: 1
skills_used: []
---

# T02: Expand terraform validate tests to cover S01 schema additions

Expand test_terraform_validate.py to exercise the new fields added in S01. For each node type, add test cases with rich configs (GPU, probes, volumes, encryption, Cloud SQL authorized_networks, Firestore CMEK, BigQuery billing model, etc). Use the Terraform MCP to verify correct attribute names when unclear.

Goal: every user-configurable field added in S01 is exercised in a terraform validate test.

## Inputs

- `docs/audit-report-s01.md`
- `Terraform MCP specs`

## Expected Output

- `Expanded test_terraform_validate.py with rich config tests per type`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
