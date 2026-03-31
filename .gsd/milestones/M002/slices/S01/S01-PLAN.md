# S01: Resource Identity — UUID Foundation

**Goal:** Every BaseNode has a stable UUID `id` field; `depends_on` uses IDs; TF resource labels use sanitized IDs; `slug` removed; existing blueprints without `id` auto-migrate; all 155 tests pass.
**Demo:** After this: After this: every node has a UUID id; depends_on uses IDs; TF resource labels are UUIDs; existing blueprints auto-migrate; all tests pass

## Tasks
- [x] **T01: Added UUID id field to BaseNode with auto-generation, removed slug, switched DAG and validation to id-keyed lookups — all 109 tests pass** — Foundation task: add `id` field to BaseNode with auto-generation, remove `slug`, update conftest `_node()` helper to generate deterministic UUIDs, switch BlueprintDAG from name-keyed to id-keyed graph, switch validation lookups from name/slug to id. This is the widest change — everything downstream depends on nodes having `id`.

## Steps

1. Edit `packages/core/core/schemas/base.py`:
   - Add `id: str = ""` field to BaseNode
   - In `resolve_config_and_validate` model_validator, add: `if not self.id: self.id = str(uuid.uuid4())` (import uuid at top)
   - Remove `slug: str = ""` field
   - Keep `name` validation (kebab-case) since name is still used for GCP resource names

2. Edit `packages/core/tests/conftest.py`:
   - Update `_node()` helper to accept `id` param, auto-generate `uuid.uuid4()` if not provided
   - Store generated IDs so tests can reference them in `depends_on`
   - Update ALL fixture `depends_on` values from name strings to ID references. Pattern: generate IDs at fixture level, pass to `_node()`, use same IDs in `depends_on` lists
   - Remove any `slug` references

3. Edit `packages/core/core/dag.py`:
   - Change `_node_map` to key by `node.id` (primary). Add `node.name` as secondary key for backward compat during transition
   - Change `_build_graph` to use `node.id` as graph keys instead of `node.name`
   - `topological_sort` returns nodes looked up by id
   - `validate_ordering` checks deps against id set
   - `parallel_batches` uses id keys

4. Edit `packages/core/core/validation.py`:
   - Replace all `slug_map`, `slug_set`, `name_set` lookups with `id_map`, `id_set`
   - `validate_depends_on` checks deps against id set
   - `validate_blueprint_by_slug` → rename to `validate_blueprint_by_id`, key results by `node.id`
   - Child-parent validation: switch from slug-based parent refs to id-based
   - Duplicate check: keep name uniqueness check but also add id uniqueness check

5. Update test files `packages/core/tests/test_dag.py` and `packages/core/tests/test_validation.py`:
   - Ensure all test envelope data uses id-based depends_on
   - Fix any assertions that reference node.slug or name-keyed results

6. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -v` — all pass

## Must-Haves

- BaseNode.id auto-generates UUID when missing (backward compat)
- slug field removed
- DAG indexes by id
- Validation uses id for all lookups
- test_dag.py and test_validation.py pass

## Negative Tests

- Envelope parsed without any `id` fields → every node gets a unique auto-generated UUID
- Duplicate node ids rejected by validation
- depends_on referencing non-existent id caught by DAG validation
  - Estimate: 1h30m
  - Files: packages/core/core/schemas/base.py, packages/core/core/dag.py, packages/core/core/validation.py, packages/core/tests/conftest.py, packages/core/tests/test_dag.py, packages/core/tests/test_validation.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_dag.py tests/test_validation.py -v
- [x] **T02: Switch all 22 TF templates and generator to use sanitized node.id (n_<uuid>) for resource labels, keeping node.name for GCP display names** — Update all 22 Jinja2 templates and the generator to use `node.id` (sanitized for TF identifier rules) as the Terraform resource label, while keeping `node.name` for GCP resource names. TF resource labels must match `[a-zA-Z_][a-zA-Z0-9_]*` — UUIDs start with digits and contain dashes, so must be sanitized (e.g. `n_<uuid_with_underscores>`).

## Steps

1. Add a `tf_resource_label` property or helper to BaseNode or a utility:
   - Takes `node.id` (UUID like `a1b2c3d4-e5f6-...`), returns TF-safe label like `n_a1b2c3d4e5f6...` (prefix `n_`, strip dashes)
   - Or add as a Jinja2 filter/global in the generator's template rendering context

2. Edit `packages/core/core/terraform/generator.py`:
   - Where template context is built (the dict passed to Jinja2), add `node_id` or `tf_label` computed from `node.id`
   - Change all `node.name` references used for TF resource naming to use the sanitized id
   - Lines using `node.name` for output names (`f"{node.name}_{out['name']}"`) → use sanitized id
   - Lines using `node.name` for binding keys → use sanitized id
   - Keep `node.name` in the context dict for GCP resource name lines (line 2 of templates)
   - The template context dict already passes `node_name` and `resource_name` — update these to use sanitized id for TF label, keep node.name for display

3. Edit all 22 templates in `packages/core/core/terraform/templates/*.tf.j2`:
   - Line 1 pattern: `resource "google_xxx" "{{ node.name }}"` → `resource "google_xxx" "{{ tf_label }}"` (or whatever variable name chosen)
   - Line 2 pattern (GCP name): `name = "${var.environment}-{{ node.name }}"` → KEEP using `node.name` (this is the human-readable GCP resource name)
   - Also update any cross-references within templates that use `node.name` as a TF label (e.g. `google_cloud_run_v2_service.{{ node.name }}`)

4. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` — all 30 tests pass

## Must-Haves

- All 22 templates use sanitized node.id for TF resource label (line 1)
- All templates keep node.name for GCP resource display name (line 2)
- Generator output names and binding keys use sanitized id
- TF resource labels are valid identifiers (no leading digit, no dashes)
- test_terraform_validate.py passes all 30 tests

## Failure Modes

- TF resource label with leading digit → terraform validate fails → must prefix
- Cross-template references (e.g. `google_service_account.{{ node.name }}.email`) must also switch to tf_label
- IAM binding safe_name uses node.name — must switch to id-based
  - Estimate: 1h30m
  - Files: packages/core/core/terraform/generator.py, packages/core/core/terraform/templates/bigquery.tf.j2, packages/core/core/terraform/templates/bigtable.tf.j2, packages/core/core/terraform/templates/cloud_dns.tf.j2, packages/core/core/terraform/templates/cloud_function.tf.j2, packages/core/core/terraform/templates/cloud_run.tf.j2, packages/core/core/terraform/templates/cloud_run_job.tf.j2, packages/core/core/terraform/templates/cloud_scheduler_job.tf.j2, packages/core/core/terraform/templates/cloud_sql.tf.j2, packages/core/core/terraform/templates/cloud_task_queue.tf.j2, packages/core/core/terraform/templates/eventarc_trigger.tf.j2, packages/core/core/terraform/templates/external_lb.tf.j2, packages/core/core/terraform/templates/firestore.tf.j2, packages/core/core/terraform/templates/gcs_bucket.tf.j2, packages/core/core/terraform/templates/pubsub_schema.tf.j2, packages/core/core/terraform/templates/pubsub_subscription.tf.j2, packages/core/core/terraform/templates/pubsub_topic.tf.j2, packages/core/core/schemas/base.py, packages/core/tests/test_terraform_validate.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
- [x] **T03: All 155 tests pass (152 passed + 3 xfailed) with zero remaining slug references in core package** — Run the full 155-test suite, fix any tests broken by the id migration that weren't caught in T01/T02, and verify backward compatibility (envelopes without id auto-migrate).

## Steps

1. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/ -v` — identify any failures
2. Fix any remaining test files that reference `slug` or use name-based depends_on
3. Verify backward compat: write a quick inline test or assertion that an Envelope parsed from JSON without `id` fields gets auto-assigned UUIDs on every node
4. Verify that `validate_blueprint_by_id` (renamed from `validate_blueprint_by_slug`) works correctly with id-keyed results
5. Check for any callers of `validate_blueprint_by_slug` in `packages/api/` or `packages/platform/` and update the import/call if needed
6. Run full suite again — all 155 tests green

## Must-Haves

- Full test suite passes (155 tests)
- No references to `slug` remain in core package (except possibly in migration comments)
- Backward compat proven: envelope without id → auto-assigns UUIDs
  - Estimate: 45m
  - Files: packages/core/tests/test_terraform_validate.py, packages/core/tests/test_dag.py, packages/core/tests/test_validation.py, packages/core/tests/conftest.py, packages/core/core/validation.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/ -v && rg -c 'slug' packages/core/core/schemas/base.py; test $? -ne 0
