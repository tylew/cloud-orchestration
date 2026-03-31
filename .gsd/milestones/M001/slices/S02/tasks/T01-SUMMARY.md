---
id: T01
parent: S02
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/core/schemas/contracts.py", "packages/core/core/schemas/configs/cloud_run.py", "packages/core/core/schemas/configs/cloud_run_job.py", "packages/core/core/schemas/configs/cloud_function.py", "packages/core/tests/test_contracts.py"]
key_decisions: ["contracts.py has no imports from configs/ to avoid circular dependencies — only config modules import from contracts"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran test_contracts.py (17/17 passed) and full test suite excluding terraform tests (126/126 passed, 0 regressions)."
completed_at: 2026-03-31T06:32:09.505Z
blocker_discovered: false
---

# T01: Define ServiceContract Pydantic models and wire into all three compute configs

> Define ServiceContract Pydantic models and wire into all three compute configs

## What Happened
---
id: T01
parent: S02
milestone: M001
key_files:
  - packages/core/core/schemas/contracts.py
  - packages/core/core/schemas/configs/cloud_run.py
  - packages/core/core/schemas/configs/cloud_run_job.py
  - packages/core/core/schemas/configs/cloud_function.py
  - packages/core/tests/test_contracts.py
key_decisions:
  - contracts.py has no imports from configs/ to avoid circular dependencies — only config modules import from contracts
duration: ""
verification_result: passed
completed_at: 2026-03-31T06:32:09.505Z
blocker_discovered: false
---

# T01: Define ServiceContract Pydantic models and wire into all three compute configs

**Define ServiceContract Pydantic models and wire into all three compute configs**

## What Happened

Created contracts.py with 6 Pydantic models (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract) per the service contract spec. Wired `contract: ServiceContract | None = None` into CloudRunConfig, CloudRunJobConfig, and CloudFunctionConfig. Wrote 17 unit tests covering model instantiation, serialization round-trips, Envelope integration for all compute types, and backward compatibility (contract=None). All 126 non-terraform tests pass with no regressions.

## Verification

Ran test_contracts.py (17/17 passed) and full test suite excluding terraform tests (126/126 passed, 0 regressions).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_contracts.py -v --tb=short` | 0 | ✅ pass | 20ms |
| 2 | `python -m pytest tests/ --tb=short -q --ignore=tests/test_terraform.py --ignore=tests/test_terraform_validate.py` | 0 | ✅ pass | 90ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/schemas/contracts.py`
- `packages/core/core/schemas/configs/cloud_run.py`
- `packages/core/core/schemas/configs/cloud_run_job.py`
- `packages/core/core/schemas/configs/cloud_function.py`
- `packages/core/tests/test_contracts.py`


## Deviations
None.

## Known Issues
None.
