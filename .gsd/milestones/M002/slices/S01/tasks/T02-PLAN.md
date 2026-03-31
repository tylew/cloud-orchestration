---
estimated_steps: 27
estimated_files: 19
skills_used: []
---

# T02: Switch TF templates and generator from node.name to sanitized node.id for resource labels

Update all 22 Jinja2 templates and the generator to use `node.id` (sanitized for TF identifier rules) as the Terraform resource label, while keeping `node.name` for GCP resource names. TF resource labels must match `[a-zA-Z_][a-zA-Z0-9_]*` — UUIDs start with digits and contain dashes, so must be sanitized (e.g. `n_<uuid_with_underscores>`).

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

## Inputs

- ``packages/core/core/schemas/base.py` — BaseNode with id field from T01`
- ``packages/core/core/terraform/generator.py` — current generator using node.name`
- ``packages/core/core/terraform/templates/*.tf.j2` — 22 templates using node.name`
- ``packages/core/tests/conftest.py` — fixtures with id-based nodes from T01`

## Expected Output

- ``packages/core/core/terraform/generator.py` — uses sanitized node.id for TF labels`
- ``packages/core/core/terraform/templates/*.tf.j2` — all 22 templates use tf_label for resource label, node.name for GCP name`
- ``packages/core/core/schemas/base.py` — tf_resource_label property or utility added`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
