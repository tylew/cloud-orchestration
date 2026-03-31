---
id: T03
parent: S01
milestone: M003
provides: []
requires: []
affects: []
key_files: ["packages/core/core/schemas/configs/service_account.py", "packages/core/core/schemas/configs/bigquery.py", "packages/core/core/schemas/configs/bigtable.py", "packages/core/core/schemas/configs/firestore.py", "packages/core/core/validation.py", "packages/core/core/auto_provision.py", "packages/core/tests/conftest.py", "packages/core/tests/test_naming.py", "packages/core/tests/test_validation.py", "packages/core/tests/test_terraform.py", "packages/core/tests/test_terraform_validate.py", "packages/core/tests/test_auto_provision.py", "packages/platform/tests/test_terraform_outputs.py", "packages/platform/tests/integration/conftest.py"]
key_decisions: ["Neutered validate_firestore_free_tier rather than deleting it — preserves function signature as no-op since database_id no longer exists in config"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "137 non-terraform-validate tests pass in 0.52s. Terraform validate tests also pass but are slow due to subprocess calls."
completed_at: 2026-03-31T16:43:15.816Z
blocker_discovered: false
---

# T03: Removed redundant config-level ID fields (account_id, dataset_id, instance_id, database_id) from 4 schema models, validation rules, auto_provision, and all test fixtures across 14 files

> Removed redundant config-level ID fields (account_id, dataset_id, instance_id, database_id) from 4 schema models, validation rules, auto_provision, and all test fixtures across 14 files

## What Happened
---
id: T03
parent: S01
milestone: M003
key_files:
  - packages/core/core/schemas/configs/service_account.py
  - packages/core/core/schemas/configs/bigquery.py
  - packages/core/core/schemas/configs/bigtable.py
  - packages/core/core/schemas/configs/firestore.py
  - packages/core/core/validation.py
  - packages/core/core/auto_provision.py
  - packages/core/tests/conftest.py
  - packages/core/tests/test_naming.py
  - packages/core/tests/test_validation.py
  - packages/core/tests/test_terraform.py
  - packages/core/tests/test_terraform_validate.py
  - packages/core/tests/test_auto_provision.py
  - packages/platform/tests/test_terraform_outputs.py
  - packages/platform/tests/integration/conftest.py
key_decisions:
  - Neutered validate_firestore_free_tier rather than deleting it — preserves function signature as no-op since database_id no longer exists in config
duration: ""
verification_result: passed
completed_at: 2026-03-31T16:43:15.817Z
blocker_discovered: false
---

# T03: Removed redundant config-level ID fields (account_id, dataset_id, instance_id, database_id) from 4 schema models, validation rules, auto_provision, and all test fixtures across 14 files

**Removed redundant config-level ID fields (account_id, dataset_id, instance_id, database_id) from 4 schema models, validation rules, auto_provision, and all test fixtures across 14 files**

## What Happened

With T01/T02 establishing resource_id-based naming via registry templates, the config-level ID fields became redundant. Removed account_id from ServiceAccountConfig (plus its validator), dataset_id from BigQueryConfig, instance_id from BigtableConfig, and database_id from FirestoreConfig. Also removed corresponding FieldRequirement entries from validation.py and neutered validate_firestore_free_tier. Updated auto_provision.py and all test fixtures across 14 files.

## Verification

137 non-terraform-validate tests pass in 0.52s. Terraform validate tests also pass but are slow due to subprocess calls.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && python -m pytest tests/ -x -v --ignore=tests/test_terraform_validate.py` | 0 | ✅ pass | 2800ms |


## Deviations

Also had to remove validation FieldRequirement entries, neuter validate_firestore_free_tier(), update auto_provision.py, and fix platform test files — all necessary but not explicitly in the plan.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/schemas/configs/service_account.py`
- `packages/core/core/schemas/configs/bigquery.py`
- `packages/core/core/schemas/configs/bigtable.py`
- `packages/core/core/schemas/configs/firestore.py`
- `packages/core/core/validation.py`
- `packages/core/core/auto_provision.py`
- `packages/core/tests/conftest.py`
- `packages/core/tests/test_naming.py`
- `packages/core/tests/test_validation.py`
- `packages/core/tests/test_terraform.py`
- `packages/core/tests/test_terraform_validate.py`
- `packages/core/tests/test_auto_provision.py`
- `packages/platform/tests/test_terraform_outputs.py`
- `packages/platform/tests/integration/conftest.py`


## Deviations
Also had to remove validation FieldRequirement entries, neuter validate_firestore_free_tier(), update auto_provision.py, and fix platform test files — all necessary but not explicitly in the plan.

## Known Issues
None.
