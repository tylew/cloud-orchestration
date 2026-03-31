# S01: resource_id on BaseNode + Registry Naming Templates

**Goal:** Every node gets an auto-generated immutable resource_id (8-char hex from UUID). Registry entries define per-type gcp_name_template. A resolve_gcp_name() function derives GCP-safe names. All TF templates use the resolved name. Config-level ID fields (account_id, dataset_id, instance_id, database_id) are removed.
**Demo:** After this: After this: every node has an auto-generated resource_id; registry entries define naming templates; config-level ID fields removed; resolve_gcp_name uses resource_id; all TF templates produce valid HCL

## Tasks
- [x] **T01: Add id/resource_id fields to BaseNode, gcp_name_template to registry, and resolve_gcp_name() function** — ## Why
This task builds the schema foundation: BaseNode gets UUID-based identity, the registry gets per-type naming templates, and a pure function resolves GCP names. All downstream work (templates, generator) depends on these.

## Steps
1. In `packages/core/core/schemas/base.py`, add to BaseNode:
   - `id: str = Field(default_factory=lambda: str(uuid4()))` — stable UUID identity
   - `resource_id: str = ""` — 8-char hex derived from id
   - A `model_validator(mode='after')` that computes `resource_id = self.id[:8].replace('-', '')` if resource_id is empty (take first 8 hex chars of UUID, which is 8 chars before the first dash)
   - Import `uuid4` from `uuid`
2. In `packages/core/core/registry.py`, add `gcp_name_template: str = ""` to ComponentDefinition dataclass. Then set templates for all 24 types:
   - cloud_run: `"{env}-{rid}"` 
   - cloud_run_job: `"{env}-{rid}"`
   - cloud_function: `"{env}-{rid}"`
   - gcs_bucket: `"{env}-{rid}"`
   - pubsub_topic: `"{env}-{rid}"`
   - pubsub_subscription: `"{env}-{rid}"`
   - pubsub_schema: `"{env}-{rid}"`
   - cloud_task_queue: `"{env}-{rid}"`
   - cloud_dns: `"{env}-{rid}"`
   - external_lb: `"{env}-{rid}"`
   - vpc: `"{rid}"`
   - subnet: `"{rid}"`
   - vpc_connector: `"{rid}"`
   - secret_manager: `"{rid}"`
   - service_account: `"sa-{rid}"` (SA max 30 chars, must start with letter)
   - bigquery: `"bq_{rid}"` (BQ requires underscores, no hyphens)
   - bigtable: `"bt-{rid}"`
   - firestore: `"(default)"` (special: Firestore default DB)
   - cloud_sql: `"{env}-{rid}"`
   - cloud_sql_database: `"{rid}"`
   - cloud_sql_table: `""` (no TF resource)
   - firestore_collection: `""` (no TF resource)
   - bigquery_table: `""` (embedded in parent)
   - third_party_api: `""` (no TF resource)
3. Create `packages/core/core/terraform/naming.py` with `resolve_gcp_name(node, env, registry)` that:
   - Looks up `gcp_name_template` from registry for node.type
   - Substitutes `{rid}` → node.resource_id, `{env}` → env string, `{name}` → node.name
   - Returns the resolved string
4. Write unit tests in `packages/core/tests/test_naming.py`:
   - Test resource_id auto-generation on BaseNode construction
   - Test resource_id is deterministic (same id → same resource_id)
   - Test resolve_gcp_name for each naming pattern category (env-prefixed, sa-prefixed, bq-underscore, firestore-default, bare rid)
   - Test that existing BaseNode construction without id/resource_id still works (defaults kick in)

## Constraints
- resource_id must be deterministic from id — derive from UUID hex, don't generate separately
- BaseNode defaults must not break existing test fixtures that don't provide id/resource_id
- Firestore template is special: "(default)" is a literal GCP name, not a pattern
  - Estimate: 1h
  - Files: packages/core/core/schemas/base.py, packages/core/core/registry.py, packages/core/core/terraform/naming.py, packages/core/tests/test_naming.py
  - Verify: cd packages/core && python -m pytest tests/test_naming.py -x -v
- [x] **T02: Wired resolve_gcp_name into TF generator and replaced all ad-hoc name patterns in 19 templates with {{ gcp_name }}** — ## Why
This is the core integration task: the generator must pass `gcp_name` into every template's context, and all 22 templates must use `{{ gcp_name }}` for the GCP resource name attribute instead of ad-hoc patterns. TF resource labels (after `resource "type"`) stay as `node.name`.

## Steps
1. In `packages/core/core/terraform/generator.py`:
   - Import `resolve_gcp_name` from `core.terraform.naming` and `REGISTRY` if not already imported
   - In the template rendering loop inside `generate_terraform()`, compute `gcp_name = resolve_gcp_name(node, global_cfg.environment, REGISTRY)` for each node
   - Add `gcp_name=gcp_name` to the `tmpl.render(...)` call kwargs
2. Update each template to use `{{ gcp_name }}` for the GCP-visible name/id attribute:
   - `service_account.tf.j2`: `account_id = "{{ gcp_name }}"` (replace `config.account_id or node.name`); also `display_name = "{{ config.display_name or gcp_name }}"`
   - `bigquery.tf.j2`: `dataset_id = "{{ gcp_name }}"` (replace `config.dataset_id`)
   - `bigtable.tf.j2`: `name = "{{ gcp_name }}"` (replace `config.instance_id`)
   - `firestore.tf.j2`: `name = "{{ gcp_name }}"` (replace `config.database_id`)
   - `secret_manager.tf.j2`: `secret_id = "{{ gcp_name }}"` (replace `config.secret_id or node.name`)
   - `cloud_run.tf.j2`: `name = "{{ gcp_name }}"` (replace `${var.environment}-{{ node.name }}`)
   - `cloud_run_job.tf.j2`: same pattern
   - `cloud_function.tf.j2`: same pattern
   - `gcs_bucket.tf.j2`: `name = "{{ gcp_name }}"` (replace `${var.environment}-{{ node.name }}`)
   - `pubsub_topic.tf.j2`: same pattern
   - `pubsub_subscription.tf.j2`: same pattern
   - `pubsub_schema.tf.j2`: same pattern
   - `cloud_task_queue.tf.j2`: same pattern
   - `cloud_dns.tf.j2`: same pattern
   - `cloud_sql.tf.j2`: same pattern
   - `vpc.tf.j2`: `name = "{{ gcp_name }}"` (replace `{{ node.name }}`)
   - `subnet.tf.j2`: same
   - `vpc_connector.tf.j2`: same
   - `external_lb.tf.j2`: base name becomes `{{ gcp_name }}`; suffixed sub-resources become `{{ gcp_name }}-ip`, `{{ gcp_name }}-cert`, etc. (replace `${var.environment}-{{ node.name }}-ip` etc.)
3. **Do NOT change** TF resource labels — `resource "type" "{{ node.name }}"` stays unchanged (these are TF-internal identifiers used by resolve_node_ref)
4. **Do NOT change** the `name =` attributes inside container/volume/env_var blocks in cloud_run/cloud_function templates — those are container-internal names, not GCP resource names
5. Run `terraform validate` tests to verify zero HCL regression

## Constraints
- external_lb has ~6 sub-resources with suffixed names — the base becomes gcp_name, suffixes stay
- secret_manager.tf.j2 uses `config.secret_id or node.name` — replace entire expression with `gcp_name`
- Templates using `${var.environment}-{{ node.name }}` — the env prefix is now inside gcp_name via the template, so remove `${var.environment}-` prefix
  - Estimate: 1.5h
  - Files: packages/core/core/terraform/generator.py, packages/core/core/terraform/templates/service_account.tf.j2, packages/core/core/terraform/templates/bigquery.tf.j2, packages/core/core/terraform/templates/bigtable.tf.j2, packages/core/core/terraform/templates/firestore.tf.j2, packages/core/core/terraform/templates/secret_manager.tf.j2, packages/core/core/terraform/templates/cloud_run.tf.j2, packages/core/core/terraform/templates/cloud_run_job.tf.j2, packages/core/core/terraform/templates/cloud_function.tf.j2, packages/core/core/terraform/templates/gcs_bucket.tf.j2, packages/core/core/terraform/templates/pubsub_topic.tf.j2, packages/core/core/terraform/templates/pubsub_subscription.tf.j2, packages/core/core/terraform/templates/pubsub_schema.tf.j2, packages/core/core/terraform/templates/cloud_task_queue.tf.j2, packages/core/core/terraform/templates/cloud_dns.tf.j2, packages/core/core/terraform/templates/cloud_sql.tf.j2, packages/core/core/terraform/templates/vpc.tf.j2, packages/core/core/terraform/templates/subnet.tf.j2, packages/core/core/terraform/templates/vpc_connector.tf.j2, packages/core/core/terraform/templates/external_lb.tf.j2
  - Verify: cd packages/core && python -m pytest tests/test_terraform_validate.py -x -v
- [ ] **T03: Remove config-level ID fields and fix all test fixtures** — ## Why
With templates now using gcp_name from the registry, config-level ID fields (account_id, dataset_id, instance_id, database_id) are redundant. Removing them completes the abstraction. Test fixtures that provide these fields must be updated.

## Steps
1. Remove config ID fields from schemas:
   - `packages/core/core/schemas/configs/service_account.py`: Remove `account_id` field and its `validate_account_id` validator. Keep `display_name`, `description`, `disabled`, `roles`.
   - `packages/core/core/schemas/configs/bigquery.py`: Remove `dataset_id` field. Other fields stay.
   - `packages/core/core/schemas/configs/bigtable.py`: Remove `instance_id` field. Other fields stay.
   - `packages/core/core/schemas/configs/firestore.py`: Remove `database_id` field. Other fields stay.
2. Update test fixtures in `packages/core/tests/conftest.py`:
   - Remove `account_id` from service_account node configs (currently `{"account_id": "my-sa"}`)
   - Remove `dataset_id` from bigquery node configs
   - Remove `instance_id` from bigtable node configs  
   - Remove `database_id` from firestore node configs
3. Search for any other test files referencing these removed fields and update them:
   - `rg 'account_id|dataset_id|instance_id|database_id' packages/core/tests/`
4. Run the full test suite including terraform validate tests
5. Also check `packages/api/` and `packages/platform/` for references to removed fields — these are read-path only and may need updates if they construct nodes

## Constraints
- bigquery.py `dataset_id` is a required field (no default) — removing it means BQ config no longer requires this. Existing blueprints in Firestore that have dataset_id will pass through Pydantic's `extra='allow'` on BaseNode but the config model may reject unknown fields depending on its settings. Check if BQ config has `extra='allow'` or not — if not, old payloads with dataset_id will fail validation. May need to add `extra='ignore'` temporarily.
- bigtable.py `instance_id` is also required — same concern.
  - Estimate: 45m
  - Files: packages/core/core/schemas/configs/service_account.py, packages/core/core/schemas/configs/bigquery.py, packages/core/core/schemas/configs/bigtable.py, packages/core/core/schemas/configs/firestore.py, packages/core/tests/conftest.py, packages/core/tests/test_terraform.py, packages/core/tests/test_terraform_validate.py, packages/core/tests/test_validation.py
  - Verify: cd packages/core && python -m pytest tests/ -x -v
