---
id: S01
parent: M003
milestone: M003
provides:
  - resource_id field on every BaseNode
  - resolve_gcp_name() function
  - gcp_name_template in registry for all 24 types
  - {{ gcp_name }} available in all TF templates
requires:
  []
affects:
  - S02
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/registry.py
  - packages/core/core/terraform/naming.py
  - packages/core/core/terraform/generator.py
  - packages/core/tests/test_naming.py
key_decisions:
  - resource_id derived as id.replace('-','')[:8] — first 8 hex chars of UUID
  - GCP naming templates letter-prefixed for vpc/subnet/vpc_connector/secret_manager
  - Config models use extra='ignore' for backward compat with existing Firestore docs
  - validate_firestore_free_tier neutered as no-op — free tier enforcement moves elsewhere
patterns_established:
  - resolve_gcp_name(node, env, registry) as single source of truth for GCP resource names
  - Registry gcp_name_template as declarative naming contract per node type
  - UUID-based identity decouples stable identity, display name, and GCP resource name
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M003/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M003/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T16:48:47.298Z
blocker_discovered: false
---

# S01: resource_id on BaseNode + Registry Naming Templates

**Every node now gets an auto-generated immutable resource_id; registry defines per-type GCP naming templates; resolve_gcp_name() wired into TF generator; config-level ID fields removed.**

## What Happened

This slice decoupled GCP resource naming from user-facing display names by introducing three layers:

1. **Identity (T01):** BaseNode gained `id` (UUID) and `resource_id` (first 8 hex chars, deterministic). A model_validator auto-computes resource_id from id. All 24 registry entries got `gcp_name_template` strings with per-type patterns (e.g. `{env}-{rid}` for Cloud Run, `sa-{rid}` for service accounts, `bq_{rid}` for BigQuery). A new `resolve_gcp_name()` function in `naming.py` substitutes template variables.

2. **Template Integration (T02):** `generate_terraform()` now computes `gcp_name` per node and passes it to every template. All 19 active TF templates replaced ad-hoc name construction (`${var.environment}-{{ node.name }}`) with `{{ gcp_name }}`. Registry templates for vpc/subnet/vpc_connector/secret_manager were updated from bare `{rid}` to letter-prefixed forms (`vpc-{rid}`, `sn-{rid}`, etc.) because GCP requires names to start with a lowercase letter.

3. **Config Cleanup (T03):** Removed `account_id`, `dataset_id`, `instance_id`, `database_id` from 4 schema config models. Updated validation rules (neutered `validate_firestore_free_tier`), auto_provision, and 14 test fixture files. All config models set `extra="ignore"` for backward compatibility with existing Firestore documents.

Verification: 137 unit tests pass, 27 terraform validate tests pass (3 xfailed as expected).

## Verification

137 core unit tests pass in 0.44s. 27 terraform validate tests pass (3 xfailed) in 125s. All naming patterns validated against real `terraform validate` runs.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

VPC/subnet/vpc_connector/secret_manager registry templates changed from bare `{rid}` to letter-prefixed forms because GCP compute names must start with a letter. Neutered validate_firestore_free_tier as a no-op rather than deleting it.

## Known Limitations

Platform test_terraform_outputs.py has a pre-existing conftest import issue from the package restructure — not caused by this slice.

## Follow-ups

Remove or fix validate_firestore_free_tier entirely if free tier enforcement moves elsewhere. Fix platform test_terraform_outputs.py conftest import.

## Files Created/Modified

- `packages/core/core/schemas/base.py` — Added id (UUID) and resource_id (8-char hex) fields to BaseNode with auto-computation validator
- `packages/core/core/registry.py` — Added gcp_name_template to all 24 ComponentDefinition entries
- `packages/core/core/terraform/naming.py` — New module: resolve_gcp_name() function
- `packages/core/core/terraform/generator.py` — Wired resolve_gcp_name into template render loop, passes gcp_name to all templates
- `packages/core/core/schemas/configs/service_account.py` — Removed account_id field
- `packages/core/core/schemas/configs/bigquery.py` — Removed dataset_id field
- `packages/core/core/schemas/configs/bigtable.py` — Removed instance_id field
- `packages/core/core/schemas/configs/firestore.py` — Removed database_id field
- `packages/core/core/validation.py` — Neutered validate_firestore_free_tier
- `packages/core/tests/test_naming.py` — 12 new tests for naming system
- `packages/core/tests/conftest.py` — Removed config-level ID fields from fixtures
