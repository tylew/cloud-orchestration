---
id: T02
parent: S02
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/validation.py", "packages/core/tests/test_refs.py"]
key_decisions: ["Ref values are plain node name slugs — lookup by name against node list, not node:name.attribute format"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py tests/test_validation.py -v — 59 passed in 0.06s"
completed_at: 2026-03-31T08:40:16.924Z
blocker_discovered: false
---

# T02: Added validate_refs() that validates all cross-resource reference fields from RESOURCE_REFS contract, checking target existence and type correctness

> Added validate_refs() that validates all cross-resource reference fields from RESOURCE_REFS contract, checking target existence and type correctness

## What Happened
---
id: T02
parent: S02
milestone: M002
key_files:
  - packages/core/core/validation.py
  - packages/core/tests/test_refs.py
key_decisions:
  - Ref values are plain node name slugs — lookup by name against node list, not node:name.attribute format
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:40:16.925Z
blocker_discovered: false
---

# T02: Added validate_refs() that validates all cross-resource reference fields from RESOURCE_REFS contract, checking target existence and type correctness

**Added validate_refs() that validates all cross-resource reference fields from RESOURCE_REFS contract, checking target existence and type correctness**

## What Happened

Implemented validate_refs() in validation.py that walks every FieldRef in RESOURCE_REFS for each node, extracts ref values from config using get_nested(), looks up target nodes by name, and verifies type matches. Handles list fields by iterating items. Wired into validate_blueprint(). Added 6 tests covering valid refs, missing targets, wrong types, optional empty refs, list context, and integration.

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py tests/test_validation.py -v — 59 passed in 0.06s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py tests/test_validation.py -v` | 0 | ✅ pass | 60ms |


## Deviations

Task plan described node:name.attribute format parsing — actual config stores plain slug names, so validation does direct name lookup instead.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/validation.py`
- `packages/core/tests/test_refs.py`


## Deviations
Task plan described node:name.attribute format parsing — actual config stores plain slug names, so validation does direct name lookup instead.

## Known Issues
None.
