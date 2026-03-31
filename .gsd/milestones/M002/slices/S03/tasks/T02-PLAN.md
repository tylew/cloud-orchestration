---
estimated_steps: 20
estimated_files: 24
skills_used: []
---

# T02: Wire resolve_gcp_name into generator and update all templates for zero-diff output

## Why
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

## Inputs

- `packages/core/core/registry.py`
- `packages/core/core/terraform/generator.py`
- `packages/core/core/terraform/templates/cloud_run.tf.j2`
- `packages/core/tests/test_naming.py`

## Expected Output

- `packages/core/core/terraform/generator.py`
- `packages/core/core/terraform/templates/cloud_run.tf.j2`
- `packages/core/core/terraform/templates/cloud_run_job.tf.j2`
- `packages/core/core/terraform/templates/cloud_function.tf.j2`
- `packages/core/core/terraform/templates/cloud_sql.tf.j2`
- `packages/core/core/terraform/templates/firestore.tf.j2`
- `packages/core/core/terraform/templates/bigtable.tf.j2`
- `packages/core/core/terraform/templates/bigquery.tf.j2`
- `packages/core/core/terraform/templates/service_account.tf.j2`
- `packages/core/core/terraform/templates/secret_manager.tf.j2`
- `packages/core/core/terraform/templates/eventarc_trigger.tf.j2`
- `packages/core/core/terraform/templates/cloud_scheduler_job.tf.j2`
- `packages/core/core/registry.py`
- `packages/core/tests/test_naming.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/ -v
