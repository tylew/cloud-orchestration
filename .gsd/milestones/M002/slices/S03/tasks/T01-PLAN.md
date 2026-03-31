---
estimated_steps: 28
estimated_files: 2
skills_used: []
---

# T01: Add naming convention fields to ComponentDefinition and resolve_gcp_name helper

## Why
The registry needs per-type GCP naming metadata so templates and the UI can derive names from a single source of truth instead of ad-hoc patterns scattered across 22 templates.

## Steps
1. Add three fields to `ComponentDefinition` dataclass in `registry.py`: `gcp_name_source` (str|None, default None — e.g. `'node.name'`, `'config.database_id'`), `gcp_name_template` (str|None, default None — e.g. `'${var.environment}-{name}'`, `'{name}'`), `gcp_name_immutable` (bool, default False).
2. Populate all 24 REGISTRY entries using this catalog:
   - `cloud_run, cloud_run_job, cloud_function, cloud_dns, cloud_task_queue, subnet, vpc, vpc_connector, gcs_bucket, pubsub_topic, pubsub_subscription, pubsub_schema, external_lb`: source=`'node.name'`, template=`'${{var.environment}}-{name}'`, immutable=False
   - `cloud_sql`: source=`'node.name'`, template=`'${{var.environment}}-{name}'`, immutable=True
   - `firestore`: source=`'config.database_id'`, template=`'{name}'`, immutable=True
   - `bigtable`: source=`'config.instance_id'`, template=`'{name}'`, immutable=True
   - `bigquery`: source=`'config.dataset_id'`, template=`'{name}'`, immutable=True
   - `service_account`: source=`'config.account_id'`, template=`'{name}'`, immutable=True (with fallback to node.name)
   - `secret_manager`: source=`'config.secret_id'`, template=`'{name}'`, immutable=False (with fallback to node.name)
   - `third_party_api`: source=None, template=None, immutable=False (no TF resource)
   - Child types (`firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table`): source=None, template=None, immutable=False
3. Create `resolve_gcp_name(node: BaseNode) -> str | None` function in `registry.py` that:
   - Looks up the ComponentDefinition for the node's type
   - If source is None, returns None
   - If source is `'node.name'`, raw_name = node.name
   - If source is `'config.X'`, raw_name = getattr(node.config, X, None) or node.name (fallback)
   - Returns template.format(name=raw_name) — but does NOT resolve `${var.environment}` (that's a TF variable, left as-is in the template string)
4. Create `packages/core/tests/test_naming.py` with tests:
   - Every REGISTRY entry with a terraform_resource has non-None gcp_name_source and gcp_name_template
   - Every REGISTRY entry without a terraform_resource (child types, third_party_api) has None source/template
   - `resolve_gcp_name` returns correct values for representative nodes of each naming pattern
   - Immutable flag is True for cloud_sql, firestore, bigtable, bigquery, service_account

## Constraints
- `ComponentDefinition` is `frozen=True` — new fields need defaults so existing code isn't broken
- The template string contains literal `${var.environment}` which is a Terraform interpolation, not a Python format string. Use a simple approach: template stores the full pattern like `${var.environment}-{name}` and resolve_gcp_name does `.format(name=raw_name)` which only replaces `{name}`

## Inputs

- `packages/core/core/registry.py`
- `packages/core/core/schemas/base.py`
- `packages/core/core/schemas/enums.py`

## Expected Output

- `packages/core/core/registry.py`
- `packages/core/tests/test_naming.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py -v
