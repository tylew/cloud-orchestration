---
id: S01
parent: M001
milestone: M001
provides:
  - Complete Pydantic schemas for all node types covering full Terraform provider fields
  - Updated Jinja2 templates for compute types
  - Audit report at docs/audit-report-s01.md
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - packages/core/schemas/configs/cloud_run.py
  - packages/core/schemas/configs/cloud_run_job.py
  - packages/core/schemas/configs/cloud_function.py
  - packages/core/schemas/configs/cloud_sql.py
  - packages/core/schemas/configs/firestore.py
  - packages/core/terraform/templates/cloud_run.tf.j2
  - packages/core/terraform/templates/cloud_run_job.tf.j2
  - packages/core/terraform/templates/cloud_function.tf.j2
  - docs/audit-report-s01.md
key_decisions:
  - All new fields use defaults for backward compat
  - Container-level fields prefixed with container_ to avoid collision
  - GPU support as string field (nvidia.com/gpu count)
  - Readiness probe modeled separately from liveness/startup probes
patterns_established:
  - Terraform MCP as ground truth source for schema audits
  - Backward-compatible schema evolution — all new fields have defaults
observability_surfaces:
  - Validation API will surface new required fields if existing blueprints are missing them
drill_down_paths:
  - .gsd/milestones/M001/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T04-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T05-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T06-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-30T23:17:28.577Z
blocker_discovered: false
---

# S01: Terraform Spec Audit & Schema Completeness

**Audited all 20 node type schemas against Terraform provider v7.25.0, filling ~100 field gaps across compute, data, messaging, network, and security types.**

## What Happened

Audited all 20 top-level node type schemas against GCP Terraform provider v7.25.0 using the HashiCorp Terraform MCP server. Compute types had the most significant gaps and received the most updates. Data types received moderate updates. Messaging, network, and security/storage types were found to be already production-adequate with minimal changes.\n\nThe audit added ~100 new fields across all schemas, all backward-compatible with defaults. Templates were updated for the three compute types. 225 unit tests pass throughout.

## Verification

225 unit tests pass. Backward compatibility verified. Audit report documents all changes.

## Requirements Advanced

- R001 — All 20 node type schemas now cover user-configurable Terraform provider fields

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02-T05 were executed more efficiently than planned — many thin schemas were already production-adequate and needed no changes. Subagent delegation worked for some types but was inconsistent, so direct editing handled the bulk.

## Known Limitations

Cloud SQL and Firestore templates not yet updated to render all new schema fields. Some advanced/niche TF fields intentionally skipped (CMEK for BigQuery, read pool auto-scaling for Cloud SQL, etc.).

## Follow-ups

Cloud SQL template could be updated to render more of the newly added fields (authorized_networks, PSC config, etc.). External LB is the most complex remaining type and could benefit from deeper audit. Subnet secondary IP ranges and log config are not yet modeled.

## Files Created/Modified

- `packages/core/schemas/configs/cloud_run.py` — Added ~30 new fields: GPU, readiness probe, grpc/tcp probes, cloud_sql/gcs/nfs volumes, description, launch_stage, encryption, IAP, container fields
- `packages/core/schemas/configs/cloud_run_job.py` — Added GPU, encryption, node_selector, direct VPC, startup probe, container fields
- `packages/core/schemas/configs/cloud_function.py` — Added description, CMEK, build config fields, available_cpu, secret env vars, direct VPC
- `packages/core/schemas/configs/cloud_sql.py` — Added authorized_networks, PSC, CMEK, data cache, password policy, location preference, deny maintenance
- `packages/core/schemas/configs/firestore.py` — Added database_edition, CMEK, Enterprise features, app engine integration mode
- `packages/core/schemas/configs/bigquery.py` — Added storage_billing_model, default_collation
- `packages/core/schemas/configs/bigtable.py` — Added display_name, force_destroy
- `packages/core/terraform/templates/cloud_run.tf.j2` — Updated template to render all new Cloud Run fields
- `packages/core/terraform/templates/cloud_run_job.tf.j2` — Updated template to render all new Cloud Run Job fields
- `packages/core/terraform/templates/cloud_function.tf.j2` — Updated template to render all new Cloud Function fields
- `docs/audit-report-s01.md` — Comprehensive audit report of all 20 node types
