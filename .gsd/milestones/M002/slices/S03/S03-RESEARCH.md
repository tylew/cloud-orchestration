# S03 — Naming Convention Contract — Research

**Date:** 2026-03-31

## Summary

S03 adds per-type GCP naming convention metadata to `ComponentDefinition` in the registry, then updates all 22 Jinja2 templates to derive GCP resource names from registry rules instead of ad-hoc patterns. This is straightforward — the patterns are already visible in the templates, they just need to be formalized into the registry dataclass and consumed consistently.

Current state: 14 types use `${var.environment}-{{ node.name }}`, 4 types use config fields directly (firestore→`database_id`, bigtable→`instance_id`, service_account→`account_id or node.name`, secret_manager→`secret_id or node.name`), bigquery uses `dataset_id`, and third_party_api generates no TF resources. Some names are immutable after creation (Firestore DB, Service Account, Cloud SQL instance, BigQuery dataset).

## Recommendation

Add three fields to `ComponentDefinition`: `gcp_name_source` (what field provides the name — `"node.name"` or `"config.X"`), `gcp_name_template` (format string like `"${var.environment}-{name}"`), and `gcp_name_immutable` (bool). Populate for all 24 registry entries. Then create a helper function that templates can call to get the GCP name, and update templates to use it. Verify with existing terraform validate tests (no HCL output should change).

## Implementation Landscape

### Key Files

- `packages/core/core/registry.py` — Add `gcp_name_source`, `gcp_name_template`, `gcp_name_immutable` to `ComponentDefinition` dataclass. Populate for all 24 REGISTRY entries.
- `packages/core/core/terraform/generator.py` — Add a `gcp_name(node, config)` helper that reads the registry and returns the resolved GCP name. Pass it to template context (or inject the resolved name directly).
- `packages/core/core/terraform/templates/*.tf.j2` — 20 templates with TF resources need the `name = ...` line updated to use the registry-derived name (either via a `gcp_name` variable or a helper function). The actual HCL output must remain identical.
- `packages/core/tests/test_naming.py` — New test file verifying registry naming metadata for all types and the gcp_name helper.

### Naming Convention Catalog (from template audit)

| Type | GCP Name Source | Template Pattern | Immutable |
|------|----------------|-----------------|-----------|
| cloud_run, cloud_run_job, cloud_function, cloud_dns, cloud_sql, cloud_task_queue, subnet, vpc, vpc_connector, gcs_bucket, pubsub_topic, pubsub_subscription, pubsub_schema, external_lb | node.name | `${var.environment}-{name}` | No (except cloud_sql: Yes) |
| firestore | config.database_id | `{value}` (no env prefix) | Yes |
| bigtable | config.instance_id | `{value}` | Yes |
| bigquery | config.dataset_id | `{value}` | Yes |
| service_account | config.account_id (fallback node.name) | `{value}` | Yes |
| secret_manager | config.secret_id (fallback node.name) | `{value}` | No |
| third_party_api | N/A | N/A (no TF resource) | N/A |
| firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table | N/A | N/A (child types, no standalone TF) | N/A |

### Build Order

1. **Registry fields + population** — Add fields to `ComponentDefinition`, populate REGISTRY. This is pure data, no behavior change. Test with a unit test that asserts all entries have naming metadata.
2. **gcp_name helper + template updates** — Create helper, update templates to use it. Verify with `terraform validate` tests that HCL output is byte-identical (zero-diff refactor).
3. **API exposure** — Add a `preview_gcp_name(node)` function for the explorer UI (S04 dependency).

### Verification Approach

- `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q` — all ~206 tests must pass
- `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` — TF validate tests confirm HCL output unchanged
- New `test_naming.py` tests: every registry entry has naming fields; `gcp_name()` returns expected values for each type
- `rg "node\.name" packages/core/core/terraform/templates/` should return zero hits after templates are updated (all replaced by registry-driven naming)

## Constraints

- `ComponentDefinition` is `frozen=True` — new fields need defaults so existing entries aren't broken during incremental population
- Templates currently use `node.name` for both TF resource label (already `tf_label` from S01) AND GCP name. Only the GCP name part changes in S03.
- Companion resources (eventarc_trigger, cloud_scheduler_job) also use `node.name` in their GCP names — these need updating too.
- Child types (firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table) have no standalone TF resources — their naming fields should be `None`/empty.

## Common Pitfalls

- **Changing HCL output** — The refactor must be zero-diff. Any change to generated HCL breaks terraform validate tests and would cause TF destroy/recreate in production. Use the existing tests as a safety net.
- **Forgetting companion resources** — eventarc_trigger and cloud_scheduler_job templates also embed `node.name` in GCP names. They're rendered separately in `_render_companion_resources()`.
