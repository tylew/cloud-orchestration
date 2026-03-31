---
id: T01
parent: S03
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/registry.py", "packages/core/tests/test_naming.py"]
key_decisions: ["Template strings stored with Python-escaped double braces ${{var.environment}} so .format() preserves Terraform interpolation"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran pytest on test_naming.py (13 passed) and full test suite excluding long-running tests (39 passed, 0 failed)."
completed_at: 2026-03-31T08:57:51.611Z
blocker_discovered: false
---

# T01: feat: add gcp_name_source, gcp_name_template, gcp_name_immutable fields to ComponentDefinition and resolve_gcp_name helper

> feat: add gcp_name_source, gcp_name_template, gcp_name_immutable fields to ComponentDefinition and resolve_gcp_name helper

## What Happened
---
id: T01
parent: S03
milestone: M002
key_files:
  - packages/core/core/registry.py
  - packages/core/tests/test_naming.py
key_decisions:
  - Template strings stored with Python-escaped double braces ${{var.environment}} so .format() preserves Terraform interpolation
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:57:51.611Z
blocker_discovered: false
---

# T01: feat: add gcp_name_source, gcp_name_template, gcp_name_immutable fields to ComponentDefinition and resolve_gcp_name helper

**feat: add gcp_name_source, gcp_name_template, gcp_name_immutable fields to ComponentDefinition and resolve_gcp_name helper**

## What Happened

Added three naming convention fields to ComponentDefinition dataclass (gcp_name_source, gcp_name_template, gcp_name_immutable) with defaults for backward compatibility. Populated all 24 REGISTRY entries with appropriate naming metadata. Created resolve_gcp_name helper that derives GCP resource names from registry rules while preserving Terraform variable interpolation. Created 13 tests covering registry invariants and name resolution behavior. All 39 existing + new tests pass.

## Verification

Ran pytest on test_naming.py (13 passed) and full test suite excluding long-running tests (39 passed, 0 failed).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py -v` | 0 | ✅ pass | 30ms |
| 2 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py tests/test_dag.py tests/test_validation.py tests/test_registry.py -v` | 0 | ✅ pass | 40ms |


## Deviations

Template strings use Python double-brace escaping for Terraform variables. Child type invariant test excludes bigquery_table/cloud_sql_database which have TF resources but derive names from parents.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/registry.py`
- `packages/core/tests/test_naming.py`


## Deviations
Template strings use Python double-brace escaping for Terraform variables. Child type invariant test excludes bigquery_table/cloud_sql_database which have TF resources but derive names from parents.

## Known Issues
None.
