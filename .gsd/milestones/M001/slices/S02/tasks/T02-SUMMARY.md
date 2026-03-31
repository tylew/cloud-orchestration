---
id: T02
parent: S02
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/core/validation.py", "packages/core/tests/test_contract_validation.py"]
key_decisions: ["Added DATA_TYPES, MESSAGING_TYPES sets to validation.py for contract type checking", "Field resolution uses container.field dot-notation with lookup into collections[].fields[] or tables[].columns[]"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 26 tests pass (15 new contract validation + 11 existing validation tests): cd packages/core && python -m pytest tests/test_contract_validation.py tests/test_validation.py -v --tb=short"
completed_at: 2026-03-31T06:34:33.594Z
blocker_discovered: false
---

# T02: Implement contract validation with cross-schema field resolution and 15 comprehensive tests

> Implement contract validation with cross-schema field resolution and 15 comprehensive tests

## What Happened
---
id: T02
parent: S02
milestone: M001
key_files:
  - packages/core/core/validation.py
  - packages/core/tests/test_contract_validation.py
key_decisions:
  - Added DATA_TYPES, MESSAGING_TYPES sets to validation.py for contract type checking
  - Field resolution uses container.field dot-notation with lookup into collections[].fields[] or tables[].columns[]
duration: ""
verification_result: passed
completed_at: 2026-03-31T06:34:33.594Z
blocker_discovered: false
---

# T02: Implement contract validation with cross-schema field resolution and 15 comprehensive tests

**Implement contract validation with cross-schema field resolution and 15 comprehensive tests**

## What Happened

Added validate_contracts() to validation.py with full validation for DataRef (node existence, data/storage type, Firestore collections with template stripping, BigQuery/CloudSQL tables, field resolution), SecretRef (secret_manager type), EventRef (messaging types), and InvokeRef (compute types). Wired into validate_blueprint(). Created 15 tests covering all positive and negative cases.

## Verification

All 26 tests pass (15 new contract validation + 11 existing validation tests): cd packages/core && python -m pytest tests/test_contract_validation.py tests/test_validation.py -v --tb=short

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && python -m pytest tests/test_contract_validation.py tests/test_validation.py -v --tb=short` | 0 | ✅ pass | 1000ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/validation.py`
- `packages/core/tests/test_contract_validation.py`


## Deviations
None.

## Known Issues
None.
