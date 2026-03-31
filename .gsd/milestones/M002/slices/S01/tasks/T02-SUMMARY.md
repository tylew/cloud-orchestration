---
id: T02
parent: S01
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/core/schemas/base.py", "packages/core/core/terraform/generator.py", "packages/core/core/terraform/resolver.py", "packages/core/core/terraform/templates/*.tf.j2", "packages/core/tests/test_terraform_validate.py", "packages/core/tests/test_cloud_dns.py"]
key_decisions: ["TF resource labels use n_ prefix + underscore-replaced UUID format", "UUID5 with test namespace for deterministic test node IDs"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 152 tests pass (27 TF validate + rest), 3 xfailed as expected."
completed_at: 2026-03-31T08:25:14.851Z
blocker_discovered: false
---

# T02: Switch all 22 TF templates and generator to use sanitized node.id (n_<uuid>) for resource labels, keeping node.name for GCP display names

> Switch all 22 TF templates and generator to use sanitized node.id (n_<uuid>) for resource labels, keeping node.name for GCP display names

## What Happened
---
id: T02
parent: S01
milestone: M002
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/terraform/generator.py
  - packages/core/core/terraform/resolver.py
  - packages/core/core/terraform/templates/*.tf.j2
  - packages/core/tests/test_terraform_validate.py
  - packages/core/tests/test_cloud_dns.py
key_decisions:
  - TF resource labels use n_ prefix + underscore-replaced UUID format
  - UUID5 with test namespace for deterministic test node IDs
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:25:14.851Z
blocker_discovered: false
---

# T02: Switch all 22 TF templates and generator to use sanitized node.id (n_<uuid>) for resource labels, keeping node.name for GCP display names

**Switch all 22 TF templates and generator to use sanitized node.id (n_<uuid>) for resource labels, keeping node.name for GCP display names**

## What Happened

Added tf_resource_label property to BaseNode. Updated generator to pass tf_label to all template renders. Updated resolver to use tf_resource_label in cross-references and id-based topological sort. Bulk-updated all 22 templates. Fixed attach_child_resources, IAM bindings, and outputs. Updated test fixtures for id-based depends_on.

## Verification

All 152 tests pass (27 TF validate + rest), 3 xfailed as expected.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_terraform_validate.py -v` | 0 | ✅ pass | 120000ms |
| 2 | `pytest tests/ -v` | 0 | ✅ pass | 122000ms |


## Deviations

Also updated resolver.py topological_sort to id-based keying, test_cloud_dns.py assertions, and attach_child_resources slug removal — all required by T01's changes.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/schemas/base.py`
- `packages/core/core/terraform/generator.py`
- `packages/core/core/terraform/resolver.py`
- `packages/core/core/terraform/templates/*.tf.j2`
- `packages/core/tests/test_terraform_validate.py`
- `packages/core/tests/test_cloud_dns.py`


## Deviations
Also updated resolver.py topological_sort to id-based keying, test_cloud_dns.py assertions, and attach_child_resources slug removal — all required by T01's changes.

## Known Issues
None.
