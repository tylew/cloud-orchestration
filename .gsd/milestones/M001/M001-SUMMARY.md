---
id: M001
title: "Terraform Audit, Deep DAG, Service Contracts & Test UI"
status: complete
completed_at: 2026-03-31T07:57:27.888Z
key_decisions:
  - D003: Terraform MCP as ground truth — validated, used successfully for S01 audit
  - D004: Replace internalGraph+WorkflowDefinition with Service Contract — design validated but implementation reverted for insufficient integration
  - Package restructure: split monolith into core/api/platform packages
  - terraform validate as test oracle pattern for generated HCL
  - Core Explorer: single HTML file with inline JS/CSS, no build step
key_files:
  - packages/core/schemas/configs/ (all 20+ config files updated)
  - packages/core/terraform/templates/ (compute templates updated)
  - packages/core/explorer/app.py
  - packages/core/explorer/static/index.html
  - packages/core/tests/test_terraform_validate.py
  - docs/audit-report-s01.md
  - docs/specs/service-contract.md
lessons_learned:
  - Building a subsystem in isolation (S02 contracts) without wiring it into real consumers leads to revert. Next time, wire into at least one real consumer (e.g., terraform generator) in the same slice.
  - Terraform MCP server is an effective ground truth for schema audits — keep using it.
  - terraform validate as test oracle catches real template bugs that unit tests miss.
  - Slice completion artifacts can diverge from code reality if code is reverted after slice completion — milestone verification must check actual code state, not just artifact status.
  - Package restructure (monolith → core/api/platform) should happen early — it simplified testing and reduced coupling.
---

# M001: Terraform Audit, Deep DAG, Service Contracts & Test UI

**Audited all 20 node type schemas against Terraform provider v7.25.0, built service contract model (later reverted for redesign), created Core Explorer test UI, and established 30 terraform validate tests as regression safety net.**

## What Happened

M001 delivered four slices across schema completeness, service contracts, test tooling, and template correctness.

**S01 (Terraform Spec Audit)** audited all 20 node type Pydantic schemas against GCP Terraform provider v7.25.0 using the HashiCorp Terraform MCP server. Added ~100 new fields across compute, data, messaging, network, and security types — all backward-compatible with defaults. Updated Jinja2 templates for Cloud Run, Cloud Run Job, and Cloud Function. Produced comprehensive audit report at docs/audit-report-s01.md.

**S05 (Fix Terraform Template Bugs)** fixed all template bugs exposed by validation tests. Enhanced the resolver for bare node names, standardized Firestore resource naming, added Cloud Function variable declarations. Expanded test suite from 14 to 30 terraform validate tests — 27 pass, 3 xfail for known edge cases.

**S02 (Deep DAG — Service Contract Model)** built ServiceContract Pydantic models, contract validation with cross-schema field resolution, DAG contract_edges(), and IAM role inference. 41 tests passed. However, the code was subsequently **reverted** (commit b87cfd2) because the contract system was built as a standalone layer disconnected from actual consumers (terraform generator, resolver, IAM renderer). The design will be revisited in a future milestone as a unified system wired into the real pipelines.

**S03 (Core Explorer Test UI)** delivered a standalone FastAPI web app for exercising the entire core package — browse all 20 resource types, build blueprints with dynamic forms from Pydantic JSON schemas, run validation, generate Terraform with per-file preview, and visualize the DAG. Zero build step (single HTML file with inline JS/CSS).

**Structural refactor:** The monolithic packages/ directory was split into standalone packages (core, api, platform) with their own pyproject.toml and test suites. internalGraph and WorkflowDefinition were archived and replaced by the Service Contract spec (docs/specs/service-contract.md), though the implementation was later reverted.

Code changes totaled 163 files changed with 8665 insertions on main. The milestone branch's S02 commits were reverted post-completion, so the net code contribution from the branch is the S02 revert plus GSD artifacts.

## Success Criteria Results

### Vision Criteria

1. **Every resource type fully maps to its Terraform spec** — ✅ MET. S01 audited all 20 types against provider v7.25.0. ~100 fields added. Audit report at docs/audit-report-s01.md.

2. **The DAG models logical data flow beyond infrastructure dependencies** — ⚠️ PARTIALLY MET then REVERTED. S02 built contract_edges() and validation, but the code was reverted (b87cfd2) because it wasn't integrated into real pipelines. The design (docs/specs/service-contract.md) is preserved for future implementation.

3. **Data contracts are defined and validated cross-node** — ⚠️ PARTIALLY MET then REVERTED. Same as above — S02 validation existed and passed 41 tests, but was reverted.

4. **A minimal test UI lets one developer exercise the full workflow** — ✅ MET. Core Explorer (packages/core/explorer/) provides type browsing, blueprint building, validation, Terraform generation, and DAG visualization.

## Definition of Done Results

1. **All slices marked complete** — ✅ All 4 slices (S01, S02, S03, S05) show ✅ in roadmap.
2. **All slice summaries exist** — ✅ S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md, S05-SUMMARY.md all present.
3. **Cross-slice integration** — ⚠️ S02's code was reverted after slice completion. S01→S05 integration works (schemas feed templates, 30 validate tests pass). S02→S03 integration partially affected (Core Explorer DAG works with infra deps but contract edges no longer exist).
4. **Tests pass** — ✅ 225+ unit tests pass. 30 terraform validate tests (27 pass, 3 xfail).

## Requirement Outcomes

### R001: Terraform Spec Completeness
**Active → Active (advanced, partially validated)**
Evidence: S01 audited all 20 schemas. S05 established 30 terraform validate tests (27 pass, 3 xfail). Templates produce valid HCL. Not fully validated because 3 xfail edge cases remain and some templates don't render all new fields yet.

### R002: Deep DAG — Logical Data Flow
**Active → Active (advanced then partially reverted)**
Evidence: S02 built contract_edges() but code was reverted. The DAG still handles infrastructure dependencies. Logical data flow needs reimplementation integrated with real pipelines.

### R003: Data Contracts — Schema Definitions Within Resources
**Active → Active (advanced then partially reverted)**
Evidence: S02 built cross-schema validation but code was reverted. Firestore/BigQuery/Cloud SQL schemas exist in config models from S01.

### R004: Workflow Specs — Compute Node References Data Contracts
**Active → Active (advanced then partially reverted)**
Evidence: S02 built ServiceContract model but code was reverted. Spec preserved at docs/specs/service-contract.md.

### R005: Dead Simple Test UI
**Active → Active (advanced)**
Evidence: Core Explorer delivers functional UI for browsing types, building blueprints, validation, Terraform generation, and DAG visualization.

### R006: Dead Code Archived
**Active → Active (not addressed)**
Evidence: S03 scope was narrowed to Core Explorer only. Dead code archival not performed.

## Deviations

S02 (Service Contract Model) was built, passed all tests, and completed as a slice — but was subsequently reverted (commit b87cfd2) because the contract system was disconnected from actual consumers (terraform generator, resolver, IAM renderer). The design is preserved at docs/specs/service-contract.md for future implementation as a properly integrated system. R006 (dead code archival) was not addressed — S03 scope was narrowed to Core Explorer only.

## Follow-ups

Reimplement service contracts integrated into terraform generator and IAM pipeline (R002, R003, R004). Fix 3 xfail terraform validate tests (dotted annotation keys, authorized_networks, vpc_connector). Archive dead frontend code (R006). Update Cloud SQL and Firestore templates to render all new S01 schema fields.
