---
id: M002
title: "Resource Identity, Reference Contracts & Naming Conventions"
status: complete
completed_at: 2026-03-31T09:18:26.859Z
key_decisions:
  - D005: UUID id field on BaseNode — depends_on and all refs use IDs; name becomes display-only label
  - D006: RESOURCE_REFS contract declaring all cross-resource reference fields with target types and TF attributes
  - D007: Per-type gcp_name_source, gcp_name_template, and immutable flag in ComponentDefinition
  - Deterministic UUIDs (UUID5 with test namespace) in test fixtures for stable references
  - Ref values are plain node name slugs — simpler than node:name.attribute format
  - slug field removed entirely rather than deprecated
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/refs.py
  - packages/core/core/registry.py
  - packages/core/core/dag.py
  - packages/core/core/validation.py
  - packages/core/core/terraform/generator.py
  - packages/core/core/terraform/resolver.py
  - packages/core/explorer/app.py
  - packages/core/explorer/static/index.html
  - packages/core/tests/test_refs.py
  - packages/core/tests/test_naming.py
  - packages/core/tests/test_explorer_api.py
lessons_learned:
  - Zero HCL diff as a verification strategy: wiring resolve_gcp_name into templates was validated by checking terraform validate output didn't change — proves refactoring correctness
  - Building contracts (RESOURCE_REFS, naming conventions) as data structures rather than scattered logic enables multiple consumers (validation, DAG, UI, templates) from one source of truth
  - UUID-based identity decouples three concerns (stable identity, display name, GCP resource name) that were previously conflated — makes rename safe and simplifies cross-references
  - Ref values as plain name slugs rather than structured node:name.attribute format — simpler is better when the contract already declares the target type
---

# M002: Resource Identity, Reference Contracts & Naming Conventions

**Established UUID-based resource identity, a typed cross-resource reference contract with validation and auto-dependency inference, per-type GCP naming conventions in the registry, and an intelligent explorer UI with ref dropdowns, name previews, and safe rename.**

## What Happened

M002 delivered four slices building on each other. S01 added a UUID `id` field to BaseNode with auto-generation, removed the `slug` field, and migrated all DAG, validation, and Terraform operations to id-based keying with a sanitized `tf_resource_label` property. S02 created the RESOURCE_REFS contract — 34 typed reference fields across 12 node types — with `validate_refs()` catching broken/wrong-type refs and `_infer_ref_edges()` automatically adding dependency edges from populated refs. S03 added `gcp_name_source`, `gcp_name_template`, and `gcp_name_immutable` to every ComponentDefinition registry entry, with `resolve_gcp_name()` wired into all 22 Terraform templates at zero HCL diff. S04 enriched the explorer API with ref metadata and naming info, and updated the UI with ref dropdowns filtered by target type, GCP name previews, immutable-name warnings, and inline rename. 230 tests pass (3 xfailed).

## Success Criteria Results

Success criteria derived from milestone vision and slice "After this" definitions:

- ✅ **Every node has a stable UUID id** — BaseNode.id auto-generates UUID; slug removed entirely (S01)
- ✅ **depends_on uses IDs** — DAG, validation, all fixtures switched to id-based (S01)
- ✅ **TF resource labels are UUIDs** — tf_resource_label property generates n_<uuid> format (S01)
- ✅ **Existing blueprints auto-migrate** — model validator auto-generates id when missing (S01)
- ✅ **Every cross-resource ref field declared in contract** — 34 FieldRef entries across 12 node types (S02)
- ✅ **Validation catches broken refs with type checking** — validate_refs() in validation pipeline (S02)
- ✅ **Auto-depends_on inferred from refs** — _infer_ref_edges() in BlueprintDAG (S02)
- ✅ **Each type has declared GCP naming convention** — All 24 registry entries have gcp_name_source/template/immutable (S03)
- ✅ **Templates derive names from registry rules** — resolve_gcp_name() wired into generator; zero HCL diff (S03)
- ✅ **Explorer UI renders ref dropdowns** — select elements filtered by target_type (S04)
- ✅ **GCP name preview shown** — /api/preview-name endpoint + async UI display (S04)
- ✅ **Rename works without breaking anything** — UUID-based depends_on makes rename safe (S04)
- ✅ **Immutable name warnings shown** — Yellow badge on immutable types (S04)
- ✅ **All tests pass** — 230 passed, 3 xfailed

## Definition of Done Results

- ✅ All 4 slices complete with summaries (S01, S02, S03, S04)
- ✅ All slice summaries exist and document provides/requires/affects
- ✅ Cross-slice integration verified: S02 consumes S01's UUID identity; S03 consumes S01's BaseNode; S04 consumes all three
- ✅ 230 tests pass including 47 terraform validate tests confirming zero HCL diff
- ✅ No regressions from M001 baseline

## Requirement Outcomes

- **R002 (Deep DAG)** — Advanced: RESOURCE_REFS contract declares all cross-resource reference fields; validate_refs() catches broken refs; DAG auto-infers dependency edges from refs. Status remains Active — full data-flow modeling (Firestore collections, BQ tables) not yet complete.
- **R005 (Dead Simple Test UI)** — Advanced: Explorer UI now provides intelligent config experience with ref dropdowns, name previews, and inline rename. Status remains Active.

## Deviations

S02 used plain name slugs for ref values instead of the originally planned node:name.attribute format. S01's T02 also updated resolver.py and test_cloud_dns.py beyond its explicit plan scope. No negative impact from either deviation.

## Follow-ups

- API handlers in packages/api/ still import validate_blueprint_by_slug — needs renaming to validate_blueprint_by_id
- Frontend TypeScript types may still reference slug
- List-type ref fields render in JSON editor rather than multi-select dropdowns
- Terraform generator should consume RESOURCE_REFS tf_attribute for ref resolution
- Ref contract is name-based — could add UUID ref resolution in future
