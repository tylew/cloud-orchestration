---
id: T02
parent: S03
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/terraform/generator.py", "packages/core/core/registry.py", "packages/core/tests/test_naming.py", "packages/core/core/terraform/templates/cloud_run.tf.j2", "packages/core/core/terraform/templates/external_lb.tf.j2"]
key_decisions: ["External LB sub-resources use {{ gcp_name }}-suffix pattern", "Scheduler job URI uses {{ gcp_name }} for consistency"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 219 existing tests pass (including terraform validate tests confirming zero HCL diff). 16 naming tests pass including 3 new preview_gcp_name tests."
completed_at: 2026-03-31T09:05:00.966Z
blocker_discovered: false
---

# T02: feat: wire resolve_gcp_name into Terraform generator and update all 22 templates to derive GCP names from registry rules with zero HCL diff

> feat: wire resolve_gcp_name into Terraform generator and update all 22 templates to derive GCP names from registry rules with zero HCL diff

## What Happened
---
id: T02
parent: S03
milestone: M002
key_files:
  - packages/core/core/terraform/generator.py
  - packages/core/core/registry.py
  - packages/core/tests/test_naming.py
  - packages/core/core/terraform/templates/cloud_run.tf.j2
  - packages/core/core/terraform/templates/external_lb.tf.j2
key_decisions:
  - External LB sub-resources use {{ gcp_name }}-suffix pattern
  - Scheduler job URI uses {{ gcp_name }} for consistency
duration: ""
verification_result: passed
completed_at: 2026-03-31T09:05:00.966Z
blocker_discovered: false
---

# T02: feat: wire resolve_gcp_name into Terraform generator and update all 22 templates to derive GCP names from registry rules with zero HCL diff

**feat: wire resolve_gcp_name into Terraform generator and update all 22 templates to derive GCP names from registry rules with zero HCL diff**

## What Happened

Wired resolve_gcp_name into generator.py's main render loop and companion resource renders (eventarc_trigger, cloud_scheduler_job). All 22 templates now use {{ gcp_name }} for the primary GCP resource name field. Added preview_gcp_name() convenience wrapper for UI display. All 219 tests pass with zero HCL diff.

## Verification

All 219 existing tests pass (including terraform validate tests confirming zero HCL diff). 16 naming tests pass including 3 new preview_gcp_name tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/ -v` | 0 | ✅ pass | 119000ms |
| 2 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py -v` | 0 | ✅ pass | 300ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/terraform/generator.py`
- `packages/core/core/registry.py`
- `packages/core/tests/test_naming.py`
- `packages/core/core/terraform/templates/cloud_run.tf.j2`
- `packages/core/core/terraform/templates/external_lb.tf.j2`


## Deviations
None.

## Known Issues
None.
