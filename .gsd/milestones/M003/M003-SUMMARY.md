---
id: M003
title: "Resource ID Abstraction & GCP Naming"
status: complete
completed_at: 2026-03-31T17:16:17.876Z
key_decisions:
  - D008: Auto-generated resource_id on BaseNode (8-char hex from UUID) — validated and implemented
  - D009: validate_firestore_free_tier neutered as no-op — free tier enforcement deferred to billing/platform layer
  - D002: Archive dead code to archive/ directory — applied to 9 insight components
  - Registry gcp_name_template uses letter-prefixed forms for vpc/subnet/vpc_connector/secret_manager to satisfy GCP naming constraints
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/registry.py
  - packages/core/core/terraform/naming.py
  - packages/core/core/terraform/generator.py
  - packages/core/tests/test_naming.py
  - apps/web/src/types/node.ts
  - apps/web/src/App.tsx
  - conftest.py
lessons_learned:
  - GCP resource names have per-type constraints (must start with letter, underscore vs hyphen) — naming templates must encode these per-type, not use a universal pattern
  - extra='ignore' on Pydantic config models provides backward compatibility when removing fields from schemas with existing Firestore documents
  - Root conftest.py with collect_ignore_glob is needed to prevent pytest from collecting archived code
  - Pre-existing test collection errors compound across milestones — fixing them as encountered in cleanup slices prevents accumulation
---

# M003: Resource ID Abstraction & GCP Naming

**Decoupled GCP resource identity from user-facing names with auto-generated resource_id, registry-driven naming templates, and config-level ID field removal across all 24 node types.**

## What Happened

M003 delivered resource identity abstraction in two slices. S01 (high risk) added UUID-based `id` and derived `resource_id` (8-char hex) to BaseNode, added `gcp_name_template` to all 24 registry entries, created `resolve_gcp_name()` as the single source of truth for GCP resource names, wired it into the Terraform generator so all 19 active templates use `{{ gcp_name }}`, and removed config-level ID fields (account_id, dataset_id, instance_id, database_id) from 4 schema models. VPC/subnet/vpc_connector/secret_manager templates needed letter-prefixed names to satisfy GCP constraints. 137 unit tests + 27 terraform validate tests pass. S02 (low) archived 9 dead insight components to archive/web-insight/, removed the insight route from App.tsx, added optional id/resource_id to the frontend BaseNode type, and fixed pre-existing test collection errors from the package split. 210 non-integration tests pass, tsc + vite builds succeed.

## Success Criteria Results

- **Every node gets auto-generated immutable resource_id:** ✅ BaseNode has UUID `id` field (default_factory) and `resource_id` computed as `id.replace('-','')[:8]` via model_validator. Verified by 12 naming tests.
- **Per-type naming templates in registry:** ✅ All 24 ComponentDefinition entries have `gcp_name_template` strings. Templates use `{env}-{rid}`, `sa-{rid}`, `bq_{rid}`, etc. per GCP naming rules.
- **Config-level ID fields removed:** ✅ account_id, dataset_id, instance_id, database_id removed from service_account, bigquery, bigtable, firestore configs. Models use `extra="ignore"` for backward compat.
- **All TF templates produce valid HCL:** ✅ 27 terraform validate tests pass (3 xfailed as expected pre-existing issues).
- **UI cleanup — no config ID fields, no dead insight code:** ✅ Frontend BaseNode type updated, 9 insight files archived, zero insight references in apps/web/src/.

## Definition of Done Results

- **S01 complete:** ✅ Summary at slices/S01/S01-SUMMARY.md
- **S02 complete:** ✅ Summary at slices/S02/S02-SUMMARY.md
- **All slice checkboxes checked:** ✅ Both S01 and S02 marked ✅ in roadmap
- **Cross-slice integration:** ✅ S02 consumed S01's resource_id field — frontend type mirrors backend model with optional id/resource_id fields

## Requirement Outcomes

- **R006 (Dead Code Archived):** active → advanced — 9 insight files archived to archive/web-insight/, insight route removed, zero insight references in working source. Not fully validated yet (other dead code may exist elsewhere).

## Deviations

VPC/subnet/vpc_connector/secret_manager registry templates changed from bare {rid} to letter-prefixed forms due to GCP naming constraints. validate_firestore_free_tier neutered rather than deleted. Pre-existing test collection errors fixed as part of S02 cleanup.

## Follow-ups

Fix packages.core.* import paths across packages/api and packages/mcp (broken since package split). Move test_terraform_outputs.py to packages/core/tests/. Remove or properly handle validate_firestore_free_tier if free tier enforcement moves to billing layer.
