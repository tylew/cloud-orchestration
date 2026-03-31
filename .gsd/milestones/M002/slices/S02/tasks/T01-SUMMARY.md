---
id: T01
parent: S02
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/refs.py", "packages/core/tests/test_refs.py"]
key_decisions: ["Used frozen dataclass for FieldRef (immutable contract entries)", "Used [] notation in dot-paths to mark list-iteration fields", "Used _MISSING sentinel instead of None to distinguish missing from null"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran pytest tests/test_refs.py — all 42 tests pass covering contract completeness, dot-path resolution on config models, target type validity, is_list consistency, and get_nested helper behavior."
completed_at: 2026-03-31T08:37:45.066Z
blocker_discovered: false
---

# T01: Created typed RESOURCE_REFS contract covering 12 node types and 30+ cross-resource reference fields with full dot-path validation against Pydantic config models

> Created typed RESOURCE_REFS contract covering 12 node types and 30+ cross-resource reference fields with full dot-path validation against Pydantic config models

## What Happened
---
id: T01
parent: S02
milestone: M002
key_files:
  - packages/core/core/refs.py
  - packages/core/tests/test_refs.py
key_decisions:
  - Used frozen dataclass for FieldRef (immutable contract entries)
  - Used [] notation in dot-paths to mark list-iteration fields
  - Used _MISSING sentinel instead of None to distinguish missing from null
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:37:45.066Z
blocker_discovered: false
---

# T01: Created typed RESOURCE_REFS contract covering 12 node types and 30+ cross-resource reference fields with full dot-path validation against Pydantic config models

**Created typed RESOURCE_REFS contract covering 12 node types and 30+ cross-resource reference fields with full dot-path validation against Pydantic config models**

## What Happened

Created packages/core/core/refs.py with FieldRef frozen dataclass and RESOURCE_REFS dict mapping NodeType to lists of FieldRef entries. Each entry declares config dot-path, target NodeType, TF attribute, and is_list flag. Contract covers all ~34 ref fields across 12 node types. Added get_nested() for runtime traversal and field_exists_on_model() for static validation with Python 3.12 UnionType support.

## Verification

Ran pytest tests/test_refs.py — all 42 tests pass covering contract completeness, dot-path resolution on config models, target type validity, is_list consistency, and get_nested helper behavior.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py -v` | 0 | ✅ pass | 30ms |


## Deviations

field_exists_on_model needed types.UnionType handling for Python 3.12. No eventarc_trigger standalone NodeType — refs declared under CLOUD_RUN's eventarc_triggers[] instead.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/refs.py`
- `packages/core/tests/test_refs.py`


## Deviations
field_exists_on_model needed types.UnionType handling for Python 3.12. No eventarc_trigger standalone NodeType — refs declared under CLOUD_RUN's eventarc_triggers[] instead.

## Known Issues
None.
