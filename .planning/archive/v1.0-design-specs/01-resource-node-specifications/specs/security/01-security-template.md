# Security/Identity Category: Rigid Template

**Category:** Security / Identity
**Types:** service_account, secret_manager
**Archetype:** Simple CRUD (see [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md))
**Provider version:** Google Terraform Provider ~5.0
**Last verified:** 2026-03-26

---

## Service Account (`service_account`)

### Terraform Resource

- Resource: `google_service_account`
- Provider version: ~5.0
- Last verified: 2026-03-26
- REGISTRY category: Identity
- is_compute: false
- iam_scope: (none -- service accounts ARE identities, not IAM targets)
- iam_terraform_resource: (none)

### State Machine

Uses **Simple CRUD** archetype. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

Standard create/update/delete lifecycle. Only `account_id` is ForceNew.

### Field Classification

#### Terraform-Mapped Fields

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| account_id | string | Yes (error) | `""` | **No (ForceNew)** | `account_id` | 6-30 chars, lowercase + hyphens, must start with letter: `^[a-z][a-z0-9-]*$` |
| display_name | string | No | `""` | Yes | `display_name` | Free text |
| description | string | No | `""` | Yes | `description` | Free text |

**ForceNew fields:**
- **account_id**: The service account ID is the primary identity. Changing it requires destroying the old SA and creating a new one. The SA email is derived: `{account_id}@{project}.iam.gserviceaccount.com`.

#### Platform-Only Fields (always mutable per D-09)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| roles | list[IamRole] | `[]` | Platform IAM metadata: tracks which GCP roles this SA should have. NOT a Terraform argument. |

**IamRole sub-model:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| role | string | (required) | GCP IAM role (e.g., "roles/cloudsql.client") |
| resource | string | `""` | Target resource (blank = project-level, otherwise resource node name) |
| description | string | `""` | Human-readable description |

**Note on roles:** The `roles` field is purely platform metadata. It tracks the INTENDED role bindings for this service account. The current `service_account.tf.j2` template generates `google_project_iam_member` resources from the roles list, but the full IAM binding generation system is deferred to Phase 6.

### Required Fields (error-level)

- **account_id**: Account ID is required. Cannot create a service account without an identifier.

### Warning Fields

None defined in REQUIRED_FIELDS.

---

## Secret Manager (`secret_manager`)

### Terraform Resource

- Resource: `google_secret_manager_secret`
- Provider version: ~5.0
- Last verified: 2026-03-26
- REGISTRY category: Security
- is_compute: false
- iam_scope: resource
- iam_terraform_resource: `google_secret_manager_secret_iam_member`

### State Machine

Uses **Simple CRUD** archetype. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

Standard create/update/delete lifecycle. `secret_id` (identity) and `replication` config are ForceNew.

### Field Classification

#### Terraform-Mapped Fields

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| secret_id | string | No | `""` (defaults to node name in TF template) | **No (ForceNew)** | `secret_id` | Valid GCP secret ID |
| description | string | No | `""` | Yes | `description` | Free text |
| replication | string | No | `"auto"` | **No (ForceNew)** | `replication.auto` / `replication.user_managed` | "auto" or "user_managed" |
| replication_locations | list[str] | No | `[]` | **No (ForceNew)** | `replication.user_managed.replicas[].location` | Valid GCP regions (only used when replication="user_managed") |
| rotation_period | string | No | `""` | Yes | `rotation.rotation_period` | Valid duration (e.g., "7776000s" = 90 days) |
| expire_time | string | No | `""` | Yes | `expire_time` | Valid RFC3339 timestamp |
| ttl | string | No | `""` | Yes | `ttl` | Valid duration (e.g., "86400s") |
| version_aliases | dict[str, str] | No | `{}` | Yes | `version_aliases` | alias -> version number mapping |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Valid label key/value |

**ForceNew fields:**
- **secret_id**: Identity field. The secret's name in Secret Manager. Changing it requires creating a new secret. Defaults to the node name if not set.
- **replication / replication_locations**: The replication strategy (automatic vs user-managed with specific locations) is permanent. Cannot change from auto to user-managed or vice versa. Cannot add/remove replication locations.

#### Platform-Only Fields (always mutable per D-09)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| value | string | `""` | The actual secret value. Stored in Firestore or set via Secret Manager API. Never in Terraform. |
| value_provided | bool | `false` | Whether the secret value has been set. UX state tracking. |
| pending_email | string | `""` | Email address to send a secure link for value provision. UX workflow support. |

### Required Fields (error-level)

None defined in REQUIRED_FIELDS. All fields have defaults. The `secret_id` defaults to empty string and falls back to the node name in the Terraform template.

### Warning Fields

None defined in REQUIRED_FIELDS.

---

*Referenced by: security/02-security-patterns.md, security/03-service-account.md, security/04-secret-manager.md*
*Phase: 01-resource-node-specifications*
