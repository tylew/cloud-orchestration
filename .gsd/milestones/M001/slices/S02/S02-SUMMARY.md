---
id: S02
parent: M001
milestone: M001
provides:
  - ServiceContract Pydantic models (contracts.py)
  - validate_contracts() in validation pipeline
  - BlueprintDAG.contract_edges() method
  - infer_iam_roles_from_contract() function
requires:
  - slice: S05
    provides: Fixed terraform templates and test infrastructure
affects:
  - S03
key_files:
  - packages/core/core/schemas/contracts.py
  - packages/core/core/validation.py
  - packages/core/core/dag.py
  - packages/core/core/iam_mappings.py
  - packages/core/tests/test_contracts.py
  - packages/core/tests/test_contract_validation.py
  - packages/core/tests/test_dag.py
  - packages/core/tests/test_iam_mappings.py
key_decisions:
  - contracts.py has no imports from configs/ to avoid circular dependencies
  - Contract access levels mapped to IAM actions via _ACCESS_TO_ACTION dict; read_write maps to Write (subsumes Read)
  - Event directions mapped: publish→Emit, subscribe→Read, enqueue→Enqueue
  - Field resolution uses container.field dot-notation with lookup into collections[].fields[] or tables[].columns[]
patterns_established:
  - ServiceContract as optional field on compute configs — backward compatible, None by default
  - Contract validation as separate function called from validate_blueprint() pipeline
  - contract_edges() returns list[tuple[str, str, str]] separate from depends_on infrastructure edges
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M001/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T06:51:28.119Z
blocker_discovered: false
---

# S02: Deep DAG — Service Contract Model

**Service contract model with typed resource refs, cross-schema validation, DAG contract edges, and IAM role inference from contracts**

## What Happened

Built the service contract subsystem in three tasks. T01 created the Pydantic model hierarchy (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract) in contracts.py and wired `contract: ServiceContract | None` into all three compute configs (CloudRun, CloudRunJob, CloudFunction) with 17 tests. T02 added validate_contracts() to validation.py implementing full cross-schema validation: DataRef checks target is a data node and resolves collections/tables/fields (with Firestore template path stripping), SecretRef validates secret_manager type, EventRef validates messaging types, InvokeRef validates compute types. Wired into validate_blueprint() pipeline. 15 tests. T03 extended BlueprintDAG with contract_edges() that extracts typed dependency edges from contracts, and added infer_iam_roles_from_contract() to iam_mappings.py mapping access levels to GCP IAM roles via the existing IAM_ROLE_MAP. 9 tests. Total: 41 new tests, 193 full suite passing.

## Verification

All 193 tests pass (150 non-terraform in 0.16s, full suite in 113s with 3 expected xfails). Contract models serialize/deserialize correctly, validation catches all invalid ref combinations, DAG surfaces contract edges, IAM inference produces correct roles.

## Requirements Advanced

- R002 — DAG now models logical data flow via contract_edges() — compute nodes referencing Firestore collections, BigQuery tables, PubSub topics surface as typed edges
- R003 — Contract validation resolves field references against Firestore collection fields, BigQuery table schemas, and Cloud SQL table columns cross-node
- R004 — Compute nodes now define ServiceContract with typed resource refs (DataRef, SecretRef, EventRef, InvokeRef) forming workflow specs for codegen

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

BigQuery test required dataset_id config field — adapted _make_node helper to accept optional config dict.

## Known Limitations

Contract validation does not yet validate GCS bucket prefix paths. InvokeRef does not validate that the target compute node's API contract is compatible.

## Follow-ups

None.

## Files Created/Modified

- `packages/core/core/schemas/contracts.py` — New: 6 Pydantic models for service contracts (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract)
- `packages/core/core/schemas/configs/cloud_run.py` — Added contract: ServiceContract | None = None field
- `packages/core/core/schemas/configs/cloud_run_job.py` — Added contract: ServiceContract | None = None field
- `packages/core/core/schemas/configs/cloud_function.py` — Added contract: ServiceContract | None = None field
- `packages/core/core/validation.py` — Added validate_contracts() with cross-schema field resolution; wired into validate_blueprint()
- `packages/core/core/dag.py` — Added contract_edges() method to BlueprintDAG
- `packages/core/core/iam_mappings.py` — Added infer_iam_roles_from_contract() function
- `packages/core/tests/test_contracts.py` — New: 17 tests for contract models
- `packages/core/tests/test_contract_validation.py` — New: 15 tests for contract validation
- `packages/core/tests/test_dag.py` — Added 3 contract_edges tests
- `packages/core/tests/test_iam_mappings.py` — Added 6 infer_iam_roles_from_contract tests
