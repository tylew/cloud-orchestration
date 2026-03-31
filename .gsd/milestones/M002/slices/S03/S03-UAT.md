# S03: Naming Convention Contract — UAT

**Milestone:** M002
**Written:** 2026-03-31T09:07:50.164Z

# S03: Naming Convention Contract — UAT

**Milestone:** M002
**Written:** 2026-03-31

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All naming behavior verified through 222 automated tests including terraform validate confirming zero HCL diff

## Preconditions

- Python 3.12 with packages/core dependencies installed
- Terraform CLI available (for terraform validate tests)

## Smoke Test

```bash
cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py -v
```
All 16 tests pass.

## Test Cases

### 1. Registry naming metadata completeness

1. Run `PYTHONPATH=. python -m pytest tests/test_naming.py::TestRegistryNamingInvariants -v`
2. **Expected:** Every entry with a terraform_resource has non-None gcp_name_source and gcp_name_template. Child types and third_party_api have None.

### 2. resolve_gcp_name for environment-prefixed types

1. Create a cloud_run node with name "my-api"
2. Call resolve_gcp_name(node)
3. **Expected:** Returns `${var.environment}-my-api`

### 3. resolve_gcp_name for config-sourced types

1. Create a firestore node with config.database_id = "mydb"
2. Call resolve_gcp_name(node)
3. **Expected:** Returns `mydb` (no environment prefix)

### 4. Immutable flag correctness

1. Check gcp_name_immutable for cloud_sql, firestore, bigtable, bigquery, service_account
2. **Expected:** All True

### 5. Zero HCL diff after template migration

1. Run `PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v`
2. **Expected:** All terraform validate tests pass — generated HCL is identical to before

### 6. preview_gcp_name for UI display

1. Call preview_gcp_name on a cloud_run node named "my-api"
2. **Expected:** Returns `<env>-my-api`

## Edge Cases

### Config field missing with fallback

1. Create a secret_manager node with no config.secret_id set
2. Call resolve_gcp_name(node)
3. **Expected:** Falls back to node.name with environment prefix

### No-TF-resource type

1. Call resolve_gcp_name on a third_party_api node
2. **Expected:** Returns None

## Failure Signals

- Any terraform validate test failure indicates HCL diff (potential production destroy/recreate)
- test_naming.py failures indicate registry metadata inconsistency

## Not Proven By This UAT

- Runtime deploy behavior with actual GCP projects
- UI rendering of preview_gcp_name (deferred to S04)

## Notes for Tester

- terraform validate tests take ~100s — they are the critical regression net
- Template strings contain literal `${var.environment}` which is Terraform interpolation, not Python
