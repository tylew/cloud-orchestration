---
id: S02
parent: M002
milestone: M002
provides:
  - RESOURCE_REFS contract (refs.py) — typed map of all cross-resource reference fields
  - validate_refs() — validation of ref existence and type correctness
  - Auto-dependency inference from refs in BlueprintDAG
requires:
  - slice: S01
    provides: UUID-based node identity and BaseNode with id field
affects:
  - S03
  - S04
key_files:
  - packages/core/core/refs.py
  - packages/core/core/validation.py
  - packages/core/core/dag.py
  - packages/core/tests/test_refs.py
key_decisions:
  - Used frozen dataclass for FieldRef (immutable contract entries)
  - Ref values are plain node name slugs — direct name lookup, not node:name.attribute parsing
  - Name-based resolution via _name_to_id dict for O(1) ref target lookup in DAG
  - Used [] notation in dot-paths to mark list-iteration fields
patterns_established:
  - RESOURCE_REFS contract as single source of truth for all cross-resource reference metadata
  - get_nested() for safe dot-path access on Pydantic models with list iteration
  - Auto-dependency inference from ref fields — no manual depends_on needed for ref-implied edges
observability_surfaces:
  - validate_refs() returns ValidationIssue list — errors surface in blueprint validation endpoint
drill_down_paths:
  - .gsd/milestones/M002/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:49:36.823Z
blocker_discovered: false
---

# S02: Reference Contract — Type-Safe Cross-Resource Wiring

**Typed RESOURCE_REFS contract declaring 34 cross-resource reference fields across 12 node types, with validate_refs() catching broken/wrong-type refs and BlueprintDAG auto-inferring dependency edges from populated refs**

## What Happened

Built the reference contract system in three tasks. T01 created `packages/core/core/refs.py` with a frozen `FieldRef` dataclass and `RESOURCE_REFS` dict mapping NodeType to lists of FieldRef entries — 34 ref fields across 12 node types covering service accounts, VPC connectors, secrets, topics, buckets, and more. Each entry declares the config dot-path, target NodeType, TF attribute, and is_list flag. Added `get_nested()` for runtime dot-path traversal and `field_exists_on_model()` for static validation against Pydantic config models. 42 tests verify contract completeness and dot-path validity.

T02 added `validate_refs()` to `validation.py` that walks RESOURCE_REFS for each node, extracts ref values using `get_nested()`, looks up target nodes by name, and verifies type matches. Handles list fields (env_vars[].secret) by iterating items. Wired into `validate_blueprint()`. Key deviation: ref values are plain node name slugs, not the `node:name.attribute` format from the original plan.

T03 added `_infer_ref_edges()` to `BlueprintDAG` that walks RESOURCE_REFS, resolves populated ref values to node IDs via a `_name_to_id` index, and adds implicit edges to the dependency graph. Called from `__init__` after `_build_graph()` so inferred edges participate in topological sort, cycle detection, and parallel batches. All 206 tests pass with no regressions.

## Verification

All 206 tests pass (206 passed, 3 xfailed) across test_refs.py (54 tests), test_validation.py (11 tests), test_dag.py (9 tests), and all other test files. No regressions from S01 baseline.

## Requirements Advanced

- R002 — RESOURCE_REFS contract declares all cross-resource reference fields; validate_refs() catches broken refs; DAG auto-infers dependency edges from refs

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Ref values are plain node name slugs instead of node:name.attribute format — simpler and matches how config actually stores references. eventarc_trigger refs declared under CLOUD_RUN's eventarc_triggers[] instead of separate NodeType.

## Known Limitations

Ref contract is name-based, not UUID-based — a future slice could add UUID ref resolution. Template resolution from refs (TF attribute lookup) is declared in the contract but not yet consumed by the Terraform generator.

## Follow-ups

S03 (Naming Convention Contract) and S04 (Explorer UI) can now consume RESOURCE_REFS for dropdown filtering and naming. Terraform generator should be updated to resolve refs via the contract's tf_attribute field.

## Files Created/Modified

- `packages/core/core/refs.py` — New — FieldRef dataclass, RESOURCE_REFS contract (34 fields across 12 node types), get_nested() helper
- `packages/core/core/validation.py` — Added validate_refs() and wired into validate_blueprint()
- `packages/core/core/dag.py` — Added _infer_ref_edges() and _name_to_id index to BlueprintDAG
- `packages/core/tests/test_refs.py` — New — 54 tests for contract completeness, validation, and DAG inference
