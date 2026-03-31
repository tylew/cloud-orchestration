---
id: S01
parent: M002
milestone: M002
provides:
  - BaseNode.id UUID field with auto-generation
  - tf_resource_label property for TF-safe identifiers
  - id-keyed DAG and validation APIs
  - validate_blueprint_by_id function
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - packages/core/core/schemas/base.py
  - packages/core/core/dag.py
  - packages/core/core/validation.py
  - packages/core/core/terraform/generator.py
  - packages/core/core/terraform/resolver.py
  - packages/core/core/terraform/templates/*.tf.j2
  - packages/core/tests/conftest.py
key_decisions:
  - Deterministic UUIDs in fixtures for stable test references
  - slug field removed entirely rather than deprecated
  - TF resource labels use n_ prefix + underscore-replaced UUID format
  - UUID5 with test namespace for deterministic test node IDs
patterns_established:
  - BaseNode.id auto-generates UUID when missing — backward compat for existing blueprints
  - tf_resource_label property on BaseNode sanitizes UUID to valid TF identifier (n_<uuid_underscored>)
  - All DAG/validation/TF operations key by node.id, not node.name
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M002/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M002/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T08:31:46.633Z
blocker_discovered: false
---

# S01: Resource Identity — UUID Foundation

**Every BaseNode now has a stable UUID id field with auto-generation; slug removed; DAG, validation, and all 22 TF templates use id-based lookups and sanitized tf_resource_label; 155 tests pass.**

## What Happened

T01 added the `id: str` field to BaseNode with UUID auto-generation in the model validator, removed the `slug` field entirely, switched BlueprintDAG to id-keyed graph operations, and updated all validation logic to use id-based lookups. The conftest `_node()` helper was updated with deterministic UUID generation for stable test references. All 109 tests passed after T01.

T02 added a `tf_resource_label` property to BaseNode that sanitizes UUIDs into valid Terraform identifiers (`n_` prefix + underscore-replaced UUID). The generator, resolver, and all 22 Jinja2 templates were updated to use `tf_label` for TF resource labels while keeping `node.name` for GCP display names. Cross-references in templates, IAM bindings, and outputs all switched to id-based labels. All 152 tests passed after T02.

T03 confirmed the full 155-test suite passes (152 passed + 3 xfailed) with zero slug references remaining in base.py. No additional fixes were needed — T01 and T02 covered all migration points.

## Verification

Full test suite: `PYTHONPATH=. python -m pytest tests/ -v` — 152 passed, 3 xfailed (155 total). Zero slug references in base.py confirmed via `rg -c slug base.py` returning exit code 1.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 also updated resolver.py topological_sort to id-based keying and test_cloud_dns.py assertions — required by T01's changes but not explicitly in T02's plan.

## Known Limitations

API handlers in packages/api/ still import `validate_blueprint_by_slug` — the function was renamed to `validate_blueprint_by_id` but external callers need updating in a future slice.

## Follow-ups

Update packages/api/ and packages/platform/ callers of the renamed validation function. Frontend node types may still reference slug in TypeScript types.

## Files Created/Modified

- `packages/core/core/schemas/base.py` — Added id field with UUID auto-generation, tf_resource_label property, removed slug
- `packages/core/core/dag.py` — Switched from name-keyed to id-keyed graph operations
- `packages/core/core/validation.py` — All lookups use id; renamed validate_blueprint_by_slug to validate_blueprint_by_id
- `packages/core/core/terraform/generator.py` — Passes tf_label to template context from node.tf_resource_label
- `packages/core/core/terraform/resolver.py` — Cross-references and topological sort use id-based keying
- `packages/core/core/terraform/templates/*.tf.j2` — All 22 templates use tf_label for TF resource labels, node.name for GCP names
- `packages/core/tests/conftest.py` — Updated _node() helper with deterministic UUID generation
- `packages/core/tests/test_dag.py` — Fixtures use id-based depends_on
- `packages/core/tests/test_validation.py` — Fixtures use id-based depends_on
- `packages/core/tests/test_terraform_validate.py` — Fixtures use id-based depends_on and updated assertions
- `packages/core/tests/test_cloud_dns.py` — Updated assertions for id-based TF labels
