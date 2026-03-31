---
id: T01
parent: S01
milestone: M003
provides: []
requires: []
affects: []
key_files: ["packages/core/core/schemas/base.py", "packages/core/core/registry.py", "packages/core/core/terraform/naming.py", "packages/core/tests/test_naming.py"]
key_decisions: ["resource_id derived as id.replace('-','')[:8] — first 8 hex chars of UUID, deterministic and collision-resistant"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran test_naming.py (12 passed) and existing test suites (test_validation, test_dag, test_registry — 38 total passed) with no regressions."
completed_at: 2026-03-31T16:24:50.871Z
blocker_discovered: false
---

# T01: Add id/resource_id fields to BaseNode, gcp_name_template to registry, and resolve_gcp_name() function

> Add id/resource_id fields to BaseNode, gcp_name_template to registry, and resolve_gcp_name() function

## What Happened
---
id: T01
parent: S01
milestone: M003
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/registry.py
  - packages/core/core/terraform/naming.py
  - packages/core/tests/test_naming.py
key_decisions:
  - resource_id derived as id.replace('-','')[:8] — first 8 hex chars of UUID, deterministic and collision-resistant
duration: ""
verification_result: passed
completed_at: 2026-03-31T16:24:50.872Z
blocker_discovered: false
---

# T01: Add id/resource_id fields to BaseNode, gcp_name_template to registry, and resolve_gcp_name() function

**Add id/resource_id fields to BaseNode, gcp_name_template to registry, and resolve_gcp_name() function**

## What Happened

Added UUID-based `id` and derived 8-char hex `resource_id` to BaseNode with auto-computation in the model validator. Added `gcp_name_template` field to all 24 ComponentDefinition registry entries with per-type naming patterns. Created `resolve_gcp_name()` in a new `naming.py` module. Wrote 12 unit tests covering all naming categories and backward compatibility.

## Verification

Ran test_naming.py (12 passed) and existing test suites (test_validation, test_dag, test_registry — 38 total passed) with no regressions.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && python -m pytest tests/test_naming.py -x -v` | 0 | ✅ pass | 30ms |
| 2 | `python -m pytest tests/test_naming.py tests/test_validation.py tests/test_dag.py tests/test_registry.py -x -q` | 0 | ✅ pass | 50ms |


## Deviations

Test helper needed minimal required configs for node types with mandatory config fields. Used CLOUD_RUN instead of VPC for backward compat test.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/schemas/base.py`
- `packages/core/core/registry.py`
- `packages/core/core/terraform/naming.py`
- `packages/core/tests/test_naming.py`


## Deviations
Test helper needed minimal required configs for node types with mandatory config fields. Used CLOUD_RUN instead of VPC for backward compat test.

## Known Issues
None.
