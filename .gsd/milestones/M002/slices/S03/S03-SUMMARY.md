---
id: S03
parent: M002
milestone: M002
provides:
  - resolve_gcp_name(node) -> str|None for any node type
  - preview_gcp_name(node) -> str|None for UI display
  - gcp_name_immutable flag per registry entry
requires:
  - slice: S01
    provides: UUID-based node identity and BaseNode with id field
affects:
  - S04
key_files:
  - packages/core/core/registry.py
  - packages/core/core/terraform/generator.py
  - packages/core/tests/test_naming.py
key_decisions:
  - Template strings use Python double-brace escaping for Terraform variables
  - External LB sub-resources use {{ gcp_name }}-suffix pattern
  - Scheduler job URI uses {{ gcp_name }} for consistency
patterns_established:
  - Registry-driven naming: all GCP resource names derived from ComponentDefinition metadata via resolve_gcp_name, not ad-hoc template patterns
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M002/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T09:07:50.164Z
blocker_discovered: false
---

# S03: Naming Convention Contract

**Per-type GCP naming conventions declared in registry with resolve_gcp_name helper wired into all 22 Terraform templates at zero HCL diff**

## What Happened

T01 added three fields to ComponentDefinition (gcp_name_source, gcp_name_template, gcp_name_immutable) and populated all 24 REGISTRY entries with naming metadata. A resolve_gcp_name helper derives GCP resource names from registry rules while preserving Terraform variable interpolation via double-brace escaping. 13 tests cover registry invariants and name resolution.

T02 wired resolve_gcp_name into generator.py's main render loop and companion resource renders (eventarc_trigger, cloud_scheduler_job). All 22 templates now use {{ gcp_name }} instead of ad-hoc patterns. A preview_gcp_name() convenience wrapper was added for the UI (replaces ${var.environment} with &lt;env&gt;). All 222 tests pass including terraform validate tests confirming zero HCL diff.

## Verification

222 tests passed (including 47 terraform validate tests confirming zero HCL diff), 3 xfailed. test_naming.py: 16 tests covering registry invariants, resolve_gcp_name behavior, and preview_gcp_name output.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

preview_gcp_name replaces ${var.environment} with &lt;env&gt; — actual environment name not available until deploy time.

## Follow-ups

None.

## Files Created/Modified

- `packages/core/core/registry.py` — Added gcp_name_source, gcp_name_template, gcp_name_immutable to ComponentDefinition; populated all 24 entries; added resolve_gcp_name and preview_gcp_name helpers
- `packages/core/core/terraform/generator.py` — Wired resolve_gcp_name into main render loop and companion resource renders
- `packages/core/tests/test_naming.py` — 16 tests for registry naming invariants, resolve_gcp_name, and preview_gcp_name
- `packages/core/core/terraform/templates/cloud_run.tf.j2` — Uses {{ gcp_name }} for resource name
- `packages/core/core/terraform/templates/external_lb.tf.j2` — Uses {{ gcp_name }}-suffix for sub-resources
