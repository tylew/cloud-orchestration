# S01 — Resource Identity (UUID Foundation) — Research

**Date:** 2026-03-31

## Summary

This slice adds a UUID `id` field to `BaseNode`, makes `depends_on` use IDs instead of names, uses IDs as TF resource labels, and provides backward-compatible migration for old blueprints. The work is straightforward in concept but wide in surface area: `node.name` is used as the TF resource label in all 22 Jinja2 templates, as the DAG graph key, as the output/IAM binding key in the generator, and as the validation lookup key. The `slug` field already exists but is vestigial — it can be removed as part of this work since `id` replaces its purpose.

The main risk is the terraform validate test suite (30 tests) — changing resource labels from `node.name` to `node.id` means every generated HCL block changes. The migration validator (auto-assign UUID when `id` is missing) must run before any other processing.

## Recommendation

Add `id: str` field to BaseNode with a model_validator that auto-generates a UUID if missing (backward compat). Change all internal lookups from name-keyed to id-keyed. Update templates and generator to use `node.id` for TF resource labels while keeping `node.name` for display/GCP naming. Remove `slug`. Update tests to include `id` in fixtures. Run terraform validate suite as the primary regression gate.

## Implementation Landscape

### Key Files

- `packages/core/core/schemas/base.py` — Add `id` field to BaseNode, auto-generate in validator, remove `slug`, keep name validation but relax it (name becomes display-only per D005)
- `packages/core/core/dag.py` — BlueprintDAG currently keys graph by `node.name`. Must switch to `node.id`. The `_node_map` indexes by both name and slug — change to index by id (primary) and name (compat lookup)
- `packages/core/core/terraform/generator.py` — Lines 367-368, 530-533: `node.name` used for output names, resource names, IAM binding keys. Switch to `node.id`
- `packages/core/core/terraform/templates/*.tf.j2` — All 22 templates use `{{ node.name }}` as TF resource label (line 1 of every template). Must become `{{ node.id }}`. The GCP name line (line 2, e.g. `name = "${var.environment}-{{ node.name }}"`) should STAY as `node.name` — that's the human-readable GCP resource name
- `packages/core/core/validation.py` — `validate_depends_on()` at line 216 checks deps against name/slug sets. Must check against id set. `validate_blueprint_by_slug()` returns results keyed by slug — should key by id
- `packages/core/tests/conftest.py` — `_node()` helper needs to generate/accept `id`. All test envelope fixtures need updating
- `packages/core/tests/test_terraform_validate.py` — Primary regression gate. Will need fixture updates for id field
- `packages/core/tests/test_dag.py`, `test_validation.py` — Need id in test data, depends_on values changed to IDs

### Build Order

1. **BaseNode schema change** — Add `id` field with auto-generation. Remove `slug`. This is the foundation everything else depends on.
2. **Test fixtures** — Update `conftest.py` `_node()` helper to auto-generate UUIDs so all tests can parse. Update `depends_on` values in fixtures to use IDs.
3. **DAG** — Switch graph keying from name to id. Small, isolated change.
4. **Validation** — Switch lookups from name/slug to id.
5. **Generator + Templates** — Switch TF resource labels from `node.name` to `node.id` in all 22 templates and generator output logic. Keep GCP names using `node.name`.
6. **Terraform validate tests** — Run full suite to confirm generated HCL is still valid.

Steps 1-2 must be first (everything else breaks without them). Steps 3-5 are somewhat parallel but generator+templates is the biggest chunk.

### Verification Approach

- `cd packages/core && PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -q` — DAG and validation tests pass
- `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` — All 30 TF validate tests pass (27 pass + 3 xfail)
- `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q` — Full test suite green
- Manual: Create envelope without `id` fields → confirm auto-migration assigns UUIDs
- Manual: Confirm generated TF uses UUID as resource label, `node.name` for GCP resource name

## Constraints

- `node.name` must remain kebab-case validated for now since it's still used in GCP resource names (line 2 of templates). The name validation in BaseNode's model_validator should stay.
- UUID format for `id` should be standard uuid4 string (no dashes is fine for TF labels, but dashes are standard — need to check TF label rules)
- Backward compat is critical: blueprints without `id` must auto-migrate silently
- The `slug` field is used in validation.py lines 193-280 for child-parent relationships (firestore collections). This logic must migrate to `id`.

## Common Pitfalls

- **TF resource labels must be valid identifiers** — UUIDs with dashes won't work as `google_cloud_run_v2_service.abc-123`. Must sanitize: replace dashes with underscores, or use a shorter format. E.g. `node_a1b2c3d4` or just strip dashes.
- **Generator output names use `node.name`** — `f"{node.name}_{out['name']}"` on line 367. These are TF output names visible to users. Consider keeping name-based outputs for readability, or switching to id-based for stability.
- **Test fixtures use name-based depends_on** — Every test fixture has `depends_on=["my-vpc", "my-sa"]`. All must switch to ID-based references, which means fixtures need deterministic or tracked UUIDs.

## Open Risks

- UUID-as-TF-resource-label format needs validation — Terraform resource labels allow `[a-zA-Z_][a-zA-Z0-9_-]*`. Standard UUID4 starts with a digit, which is invalid. Must prefix (e.g. `n_<uuid>`) or use a different format.
- The explorer app (`packages/core/explorer/`) likely references nodes by name — may need updating but is low priority for this slice.
