# S01 — Research: resource_id on BaseNode + Registry Naming Templates

**Date:** 2026-03-31

## Summary

This slice adds auto-generated `resource_id` (8-char hex from UUID) to `BaseNode`, adds per-type `gcp_name_template` to `ComponentDefinition` in the registry, removes config-level ID fields (`account_id`, `dataset_id`, `instance_id`, `database_id`), creates a `resolve_gcp_name(node, env)` function, and rewires all 22 TF templates to use the resolved name instead of ad-hoc patterns.

The codebase is well-structured for this. `BaseNode` in `packages/core/core/schemas/base.py` needs one new field. `ComponentDefinition` in `packages/core/core/registry.py` needs 1-2 new fields. The 22 Jinja2 templates use `node.name` ~77 times for TF resource naming — each needs updating to use the registry-derived name. The `resolve_node_ref` function in `resolver.py` uses `node.name` as the TF resource label and needs updating. Four config schemas have ID fields to remove: `service_account.py` (`account_id`), `bigquery.py` (`dataset_id`), `bigtable.py` (`instance_id`), `firestore.py` (`database_id`).

The primary risk is breaking TF template output. The `test_terraform_validate.py` suite (~100s runtime) is the regression safety net — it runs `terraform validate` on generated HCL. The zero-diff strategy from Knowledge (generate before/after and compare) is the right verification approach.

## Recommendation

Build bottom-up: schema changes first (BaseNode + registry), then `resolve_gcp_name()`, then rewire templates, then remove config ID fields. Use `terraform validate` tests as the primary regression oracle. Wire `resolve_gcp_name` into the generator so templates receive a `gcp_name` variable instead of computing names ad-hoc.

## Implementation Landscape

### Key Files

- `packages/core/core/schemas/base.py` — Add `id: str` (UUID4) and `resource_id: str` (8-char hex derived from id) to BaseNode. Both auto-generated with defaults. The `name` field stays but kebab-case validation stays (it's still the TF resource label).
- `packages/core/core/registry.py` — Add `gcp_name_template: str` to `ComponentDefinition`. Examples: `"sa-{rid}"` for service_account, `"bq_{rid}"` for bigquery (underscores for BQ), `"{env}-{name}"` for cloud_run. Add entries for all 24 types.
- `packages/core/core/terraform/resolver.py` — Add `resolve_gcp_name(node, env, registry)` function. Also update `resolve_node_ref` to use `node.name` as TF label (this doesn't change — TF resource labels aren't GCP names).
- `packages/core/core/terraform/generator.py` — Pass `gcp_name` to template context alongside `node` and `config`. Currently templates receive `node`, `config`, `global`, `resolve_ref`.
- `packages/core/core/terraform/templates/*.tf.j2` — All 22 templates. Replace ad-hoc `name = "${var.environment}-{{ node.name }}"` and `account_id = "{{ config.account_id }}"` patterns with `{{ gcp_name }}`.
- `packages/core/core/schemas/configs/service_account.py` — Remove `account_id` field and its validator.
- `packages/core/core/schemas/configs/bigquery.py` — Remove `dataset_id` field.
- `packages/core/core/schemas/configs/bigtable.py` — Remove `instance_id` field.
- `packages/core/core/schemas/configs/firestore.py` — Remove `database_id` field (note: `"(default)"` is a valid Firestore DB name, needs special handling in naming template).
- `packages/core/core/validation.py` — Uses `node.name` for error messages only (no change needed).
- `packages/api/handlers/nodes.py` — `create_node` calls `BaseNode.model_validate(payload)` — UUID/resource_id auto-generation happens in BaseNode defaults, no API change needed.
- `packages/core/tests/test_terraform_validate.py` — Primary regression test (~100s). Run before and after to confirm zero HCL breakage.
- `packages/core/tests/test_terraform.py` — Unit tests for generator output. Will need updates for new template variables.
- `packages/core/tests/conftest.py` — Test fixtures creating BaseNode instances may need `id`/`resource_id` fields or rely on defaults.

### Current Naming Patterns in Templates

| Type | Current TF `name =` pattern | Source |
|------|---------------------------|--------|
| cloud_run, cloud_run_job | `${var.environment}-{{ node.name }}` | env prefix |
| gcs_bucket, pubsub_sub | `${var.environment}-{{ node.name }}` | env prefix |
| service_account | `{{ config.account_id or node.name }}` | config field |
| bigquery | `{{ config.dataset_id }}` | config field |
| bigtable | `{{ config.instance_id }}` | config field |
| firestore | `{{ config.database_id }}` | config field |
| secret_manager | `{{ config.secret_id or node.name }}` | config field |
| external_lb | `${var.environment}-{{ node.name }}-ip` (multiple sub-resources) | env prefix + suffix |
| vpc, subnet, vpc_connector | `{{ node.name }}` or env-prefixed | bare name |

### Build Order

1. **BaseNode schema + registry changes** — Add `id`/`resource_id` to BaseNode, add `gcp_name_template` to ComponentDefinition with all 24 entries. Unit-testable in isolation.
2. **`resolve_gcp_name()` function** — Pure function, testable with unit tests against registry entries. Handles `{rid}`, `{env}`, `{name}` placeholders.
3. **Generator wiring** — Pass `gcp_name` into template context. This is the integration point.
4. **Template rewiring** — Update all 22 templates to use `{{ gcp_name }}` for the GCP resource name field. TF resource *labels* (the `"{{ node.name }}"` after `resource "type"`) stay as `node.name`.
5. **Remove config ID fields** — Only after templates no longer reference them.
6. **Test fixture updates** — Update any test that constructs BaseNode or expects old config fields.

### Verification Approach

1. Run `terraform validate` tests before starting: `cd packages/core && python -m pytest tests/test_terraform_validate.py -x` — capture baseline.
2. After template rewiring, run same tests — must still pass.
3. Unit tests for `resolve_gcp_name()` covering all naming patterns.
4. Run full test suite: `cd packages/core && python -m pytest tests/ -x`

## Constraints

- TF resource **labels** (e.g., `resource "google_service_account" "{{ node.name }}"`) must remain `node.name` — they're used by `resolve_node_ref()` for cross-resource references. Only the GCP-visible `name`/`account_id`/`dataset_id` attribute changes.
- `resource_id` must be deterministic from `id` (UUID) — not random on every access. Generate once at creation, store immutably.
- Firestore `database_id = "(default)"` is a valid special value. The naming template for firestore type needs to handle this (perhaps `gcp_name_template` defaults to `"{rid}"` but firestore overrides to `"(default)"` or the template uses a conditional).
- BigQuery `dataset_id` requires underscores only (no hyphens). The naming template must produce `bq_{rid}` or similar.
- Service account `account_id` max 30 chars, pattern `^[a-z][a-z0-9-]*$`. 8-char hex `resource_id` with prefix fits easily.
- `external_lb` template creates ~6 sub-resources with suffixed names (`_ip`, `_cert`, `_neg`, etc.) — `gcp_name` is the base; suffixes stay in template.

## Common Pitfalls

- **Changing TF resource labels breaks state** — Only change the `name =` attribute inside the resource block, NOT the label after `resource "type"`. The label is TF-internal and changing it forces destroy/recreate.
- **Test fixtures without id/resource_id** — If BaseNode requires these, every test fixture breaks. Use `default_factory=uuid4` and auto-derive `resource_id` so existing test code works unchanged.
- **Firestore "(default)" database** — This is the only type where the GCP name isn't derived from resource_id. Handle as special case in the naming template or allow override.
