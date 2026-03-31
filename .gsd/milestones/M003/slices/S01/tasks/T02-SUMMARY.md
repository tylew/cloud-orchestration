---
id: T02
parent: S01
milestone: M003
provides: []
requires: []
affects: []
key_files: ["packages/core/core/terraform/generator.py", "packages/core/core/registry.py", "packages/core/core/terraform/templates/cloud_run.tf.j2", "packages/core/core/terraform/templates/external_lb.tf.j2", "packages/core/core/terraform/templates/service_account.tf.j2", "packages/core/tests/test_naming.py"]
key_decisions: ["VPC/subnet/vpc_connector/secret_manager registry templates changed from bare {rid} to letter-prefixed forms because GCP compute names must start with a letter"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "pytest tests/test_terraform_validate.py: 27 passed, 3 xfailed. pytest tests/test_naming.py: 12 passed."
completed_at: 2026-03-31T16:34:21.145Z
blocker_discovered: false
---

# T02: Wired resolve_gcp_name into TF generator and replaced all ad-hoc name patterns in 19 templates with {{ gcp_name }}

> Wired resolve_gcp_name into TF generator and replaced all ad-hoc name patterns in 19 templates with {{ gcp_name }}

## What Happened
---
id: T02
parent: S01
milestone: M003
key_files:
  - packages/core/core/terraform/generator.py
  - packages/core/core/registry.py
  - packages/core/core/terraform/templates/cloud_run.tf.j2
  - packages/core/core/terraform/templates/external_lb.tf.j2
  - packages/core/core/terraform/templates/service_account.tf.j2
  - packages/core/tests/test_naming.py
key_decisions:
  - VPC/subnet/vpc_connector/secret_manager registry templates changed from bare {rid} to letter-prefixed forms because GCP compute names must start with a letter
duration: ""
verification_result: passed
completed_at: 2026-03-31T16:34:21.146Z
blocker_discovered: false
---

# T02: Wired resolve_gcp_name into TF generator and replaced all ad-hoc name patterns in 19 templates with {{ gcp_name }}

**Wired resolve_gcp_name into TF generator and replaced all ad-hoc name patterns in 19 templates with {{ gcp_name }}**

## What Happened

Imported resolve_gcp_name in generator.py and added gcp_name computation to the template render loop. Updated all 19 TF templates to use {{ gcp_name }} for GCP-visible name attributes. Fixed registry gcp_name_template for vpc/subnet/vpc_connector/secret_manager to use letter prefixes since GCP compute names must start with a lowercase letter.

## Verification

pytest tests/test_terraform_validate.py: 27 passed, 3 xfailed. pytest tests/test_naming.py: 12 passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_terraform_validate.py -x -v` | 0 | ✅ pass | 152000ms |
| 2 | `python -m pytest tests/test_naming.py -v` | 0 | ✅ pass | 40ms |


## Deviations

Changed vpc/subnet/vpc_connector/secret_manager registry gcp_name_template from bare {rid} to prefixed forms (vpc-{rid}, sn-{rid}, conn-{rid}, sc-{rid}) because GCP compute names must start with a lowercase letter.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/terraform/generator.py`
- `packages/core/core/registry.py`
- `packages/core/core/terraform/templates/cloud_run.tf.j2`
- `packages/core/core/terraform/templates/external_lb.tf.j2`
- `packages/core/core/terraform/templates/service_account.tf.j2`
- `packages/core/tests/test_naming.py`


## Deviations
Changed vpc/subnet/vpc_connector/secret_manager registry gcp_name_template from bare {rid} to prefixed forms (vpc-{rid}, sn-{rid}, conn-{rid}, sc-{rid}) because GCP compute names must start with a lowercase letter.

## Known Issues
None.
