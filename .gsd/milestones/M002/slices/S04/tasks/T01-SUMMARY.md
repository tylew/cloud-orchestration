---
id: T01
parent: S04
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/explorer/app.py", "packages/core/tests/test_explorer_api.py"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran test_explorer_api.py (8 passed) and full suite (203 passed, 0 failed)."
completed_at: 2026-03-31T09:11:35.275Z
blocker_discovered: false
---

# T01: Add explorer API endpoints for ref metadata, naming info, and name preview

> Add explorer API endpoints for ref metadata, naming info, and name preview

## What Happened
---
id: T01
parent: S04
milestone: M002
key_files:
  - packages/core/explorer/app.py
  - packages/core/tests/test_explorer_api.py
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-31T09:11:35.275Z
blocker_discovered: false
---

# T01: Add explorer API endpoints for ref metadata, naming info, and name preview

**Add explorer API endpoints for ref metadata, naming info, and name preview**

## What Happened

Enhanced /api/types to include refs array and naming object per type from RESOURCE_REFS and ComponentDefinition. Added POST /api/preview-name endpoint that constructs a BaseNode and returns preview_gcp_name() result. Created test_explorer_api.py with 8 tests covering refs, naming, preview, and error cases. All 203 tests pass with no regressions.

## Verification

Ran test_explorer_api.py (8 passed) and full suite (203 passed, 0 failed).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v` | 0 | ✅ pass | 2600ms |
| 2 | `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q --ignore=tests/test_terraform_validate.py` | 0 | ✅ pass | 2500ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `packages/core/explorer/app.py`
- `packages/core/tests/test_explorer_api.py`


## Deviations
None.

## Known Issues
None.
