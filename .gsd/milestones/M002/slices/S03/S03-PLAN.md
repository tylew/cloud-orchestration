# S03: Naming Convention Contract

**Goal:** Each resource type has a declared GCP naming convention in the registry; a helper resolves names from registry rules; templates derive names via the helper; immutable names flagged; naming is consistent across all types.
**Demo:** After this: After this: each resource type has a declared GCP naming convention in the registry; templates derive names from registry rules; immutable names flagged; naming is consistent across all types

## Tasks
- [x] **T01: feat: add gcp_name_source, gcp_name_template, gcp_name_immutable fields to ComponentDefinition and resolve_gcp_name helper** — ## Why
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
  - Estimate: 45m
  - Files: packages/core/core/registry.py, packages/core/tests/test_naming.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_naming.py -v
- [x] **T02: feat: wire resolve_gcp_name into Terraform generator and update all 22 templates to derive GCP names from registry rules with zero HCL diff** — ## Why
The registry now has naming metadata and a helper function. Templates still use ad-hoc `node.name` and `config.X` for GCP names. This task wires the helper into the generator so templates receive a `gcp_name` variable and updates all 22 templates to use it — with zero change to generated HCL.

## Steps
1. In `generator.py`, import `resolve_gcp_name` from `core.registry`.
2. In the main render loop (around line 450 where `tmpl.render(...)` is called), compute `gcp_name = resolve_gcp_name(node)` and pass it as an additional template variable: `gcp_name=gcp_name`.
3. Also pass `gcp_name` in `_render_companion_resources()` for eventarc_trigger and cloud_scheduler_job templates.
4. Update each of the 22 templates that have TF resources:
   - Templates using `${{var.environment}}-{{ node.name }}` for the name/id field → replace with `{{ gcp_name }}`
   - Templates using `{{ config.database_id }}`, `{{ config.instance_id }}`, `{{ config.dataset_id }}` for name → replace with `{{ gcp_name }}`
   - Templates using `{{ config.account_id or node.name }}` → replace with `{{ gcp_name }}`
   - Templates using `{{ config.secret_id or node.name }}` → replace with `{{ gcp_name }}`
   - `third_party_api.tf.j2` — no TF resource, may just have a comment; no name field to change
   - eventarc_trigger.tf.j2 and cloud_scheduler_job.tf.j2 — these use `${{var.environment}}-{{ node.name }}` in their GCP name fields; replace with `{{ gcp_name }}`
5. **Critical**: The `resolve_gcp_name` helper returns the FULL string including `${var.environment}-` prefix where applicable. So `{{ gcp_name }}` in the template must produce the exact same HCL as the old pattern. Verify by running terraform validate tests.
6. Run the full test suite to confirm zero-diff.
7. Add a `preview_gcp_name(node: BaseNode) -> str | None` convenience wrapper in registry.py that returns a human-readable preview (replacing `${var.environment}` with `<env>`) for S04's UI use.

## Constraints
- HCL output must be byte-identical — any difference breaks terraform validate tests and would cause TF destroy/recreate in production
- `node.name` is still used in templates for display_name, description, and comments — only the GCP resource name field changes
- Some templates use `node.name` in multiple places (e.g. display_name). Only replace the one that is the GCP resource identifier (name, account_id, secret_id, etc.)
  - Estimate: 1h
  - Files: packages/core/core/terraform/generator.py, packages/core/core/terraform/templates/cloud_run.tf.j2, packages/core/core/terraform/templates/cloud_run_job.tf.j2, packages/core/core/terraform/templates/cloud_function.tf.j2, packages/core/core/terraform/templates/cloud_sql.tf.j2, packages/core/core/terraform/templates/cloud_dns.tf.j2, packages/core/core/terraform/templates/vpc.tf.j2, packages/core/core/terraform/templates/subnet.tf.j2, packages/core/core/terraform/templates/vpc_connector.tf.j2, packages/core/core/terraform/templates/gcs_bucket.tf.j2, packages/core/core/terraform/templates/pubsub_topic.tf.j2, packages/core/core/terraform/templates/pubsub_subscription.tf.j2, packages/core/core/terraform/templates/pubsub_schema.tf.j2, packages/core/core/terraform/templates/external_lb.tf.j2, packages/core/core/terraform/templates/cloud_task_queue.tf.j2, packages/core/core/terraform/templates/firestore.tf.j2, packages/core/core/terraform/templates/bigtable.tf.j2, packages/core/core/terraform/templates/bigquery.tf.j2, packages/core/core/terraform/templates/service_account.tf.j2, packages/core/core/terraform/templates/secret_manager.tf.j2, packages/core/core/terraform/templates/eventarc_trigger.tf.j2, packages/core/core/terraform/templates/cloud_scheduler_job.tf.j2, packages/core/core/registry.py, packages/core/tests/test_naming.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/ -v
