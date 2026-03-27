# Service Account: Specifics

**Type:** service_account
**Terraform Resource:** `google_service_account`
**Archetype:** Simple CRUD
**Complexity:** Lowest of all types (4 config fields, 1 sub-model)

---

## Overview

Service Account is one of the simplest node types in the platform. It has only 4 config fields (3 Terraform-mapped, 1 platform-only). Its primary purpose is to provide an identity for compute resources to run under, and to track intended IAM role bindings.

## Account ID and Email Derivation

The `account_id` field is the core identity of a service account. From it, GCP derives the full SA email:

```
{account_id}@{project_id}.iam.gserviceaccount.com
```

For example, if `account_id = "my-api-sa"` and the project is `dev-abc123`:
```
my-api-sa@dev-abc123.iam.gserviceaccount.com
```

### Naming Constraints

The `account_id` field has strict validation (enforced by `ServiceAccountConfig.validate_account_id`):

| Constraint | Rule |
|-----------|------|
| Minimum length | 6 characters (GCP requirement, not enforced in current validator) |
| Maximum length | 30 characters |
| Character set | Lowercase letters, digits, and hyphens |
| Pattern | `^[a-z][a-z0-9-]*$` (must start with a letter) |
| Uniqueness | Must be unique within the GCP project |

**Note on minimum length:** GCP requires account_id to be at least 6 characters, but the current Pydantic validator only enforces the maximum (30) and the regex pattern. The 6-character minimum should be added as a validation enhancement.

### ForceNew Implications

Since `account_id` is ForceNew, changing it means:
1. The old SA (`old-id@project.iam.gserviceaccount.com`) is destroyed.
2. A new SA (`new-id@project.iam.gserviceaccount.com`) is created.
3. All IAM bindings on the old SA are lost.
4. All compute resources referencing the old SA email will break until updated.

The platform should treat account_id changes as high-impact and warn users accordingly.

## Terraform Template Behavior

The `service_account.tf.j2` template has two notable behaviors:

### Account ID Fallback

```jinja2
account_id = "{{ config.account_id or node.name }}"
```

If `account_id` is not set, it falls back to the node name. This is a convenience but can cause issues if the node name doesn't meet SA naming constraints.

### Display Name Fallback

```jinja2
display_name = "{{ config.display_name or config.account_id }}"
```

If `display_name` is not set, it falls back to the account_id. This provides a reasonable default.

### IAM Binding Generation

The template also generates `google_project_iam_member` resources for each role:

```jinja2
{% for binding in config.roles %}
resource "google_project_iam_member" "{{ node.name }}_{{ loop.index0 }}" {
  project = var.gcp_project_id
  role    = "{{ binding.role }}"
  member  = "serviceAccount:${google_service_account.{{ node.name }}.email}"
}
{% endfor %}
```

This generates project-level IAM bindings. Resource-level bindings (e.g., `roles/secretmanager.secretAccessor` on a specific secret) require a different Terraform resource per target type, which is deferred to Phase 6.

## Integration Points

### Compute Type References

Every compute type has a required `service_account` field that should reference a service_account node:

| Compute Type | Field | Severity |
|-------------|-------|----------|
| cloud_run | service_account | error |
| cloud_run_job | service_account | error |
| cloud_function | service_account | error |

The reference can be:
- A direct SA email string: `"my-sa@project.iam.gserviceaccount.com"`
- A node reference: `"node:my-sa"` (resolved to the SA email at TF generation time via `resolve_ref`)

### Validation

The validation module (`validation.py`) checks:
- `iam.service_account` references point to existing nodes of type `service_account`.
- `invoker_bindings[].service_account` references point to existing SA nodes.
- `accessor_bindings[].service_account` references point to existing SA nodes.

### Deploy Ordering

Service accounts must be deployed BEFORE compute resources that reference them. The DAG module (`dag.py`) handles this ordering via the `depends_on` edges and implicit dependencies from `iam.service_account` references.

---

*References: [01-security-template.md](01-security-template.md), [02-security-patterns.md](02-security-patterns.md)*
*Phase: 01-resource-node-specifications*
