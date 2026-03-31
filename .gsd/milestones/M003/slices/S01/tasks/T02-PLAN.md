---
estimated_steps: 34
estimated_files: 20
skills_used: []
---

# T02: Wire resolve_gcp_name into generator and rewrite all TF templates

## Why
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

## Inputs

- ``packages/core/core/terraform/naming.py``
- ``packages/core/core/terraform/generator.py``
- ``packages/core/core/terraform/templates/cloud_run.tf.j2``
- ``packages/core/core/terraform/templates/service_account.tf.j2``
- ``packages/core/core/terraform/templates/bigquery.tf.j2``
- ``packages/core/core/terraform/templates/bigtable.tf.j2``
- ``packages/core/core/terraform/templates/firestore.tf.j2``

## Expected Output

- ``packages/core/core/terraform/generator.py``
- ``packages/core/core/terraform/templates/service_account.tf.j2``
- ``packages/core/core/terraform/templates/bigquery.tf.j2``
- ``packages/core/core/terraform/templates/bigtable.tf.j2``
- ``packages/core/core/terraform/templates/firestore.tf.j2``
- ``packages/core/core/terraform/templates/cloud_run.tf.j2``
- ``packages/core/core/terraform/templates/external_lb.tf.j2``

## Verification

cd packages/core && python -m pytest tests/test_terraform_validate.py -x -v
