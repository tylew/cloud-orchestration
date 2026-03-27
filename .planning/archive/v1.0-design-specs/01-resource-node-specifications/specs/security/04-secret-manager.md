# Secret Manager: Specifics

**Type:** secret_manager
**Terraform Resource:** `google_secret_manager_secret`
**Archetype:** Simple CRUD
**Complexity:** Medium (11 config fields, 0 nested sub-models, but dual lifecycle)

---

## Overview

Secret Manager has a dual lifecycle: Terraform manages the secret resource (container, replication, metadata), while the platform manages secret versions (actual values). This split is by design -- secret values should never appear in Terraform state files. The type has 11 fields total: 8 Terraform-mapped and 3 platform-only.

## Replication Immutability

The `replication` field is the most important ForceNew field on secret_manager. It determines how the secret data is replicated across GCP regions.

### Replication Options

| Value | Behavior | Use Case |
|-------|----------|----------|
| `"auto"` | GCP automatically replicates across regions | Default, simplest option |
| `"user_managed"` | User specifies exact regions via `replication_locations` | Compliance requirements, data residency |

### Why ForceNew

- Replication strategy is baked into the secret's storage infrastructure.
- Changing from `auto` to `user_managed` (or vice versa) would require migrating all secret versions across different storage backends.
- GCP does not support this migration -- a new secret must be created.

### Practical Impact

If a user needs to change replication strategy:
1. Create a new secret with the desired replication config.
2. Copy the value from the old secret to the new one.
3. Update all references to point to the new secret.
4. Delete the old secret.

The platform should guide users through this process rather than silently destroying and recreating (which would lose all secret versions).

## Secret Value Management

The value/value_provided/pending_email fields form a platform-level UX workflow:

### Value Provision Flow

1. **Secret created without value:** `value=""`, `value_provided=false`. The secret resource exists in GCP but has no versions.
2. **Value assignment requested:** `pending_email="alice@company.com"`. The platform could send a secure link for Alice to provide the value.
3. **Value provided:** `value="the-secret"`, `value_provided=true`, `pending_email=""`. The platform creates a secret version via the Secret Manager API.

### Security Considerations

- The `value` field is stored in Firestore (platform database), NOT in Terraform state.
- Access to the value in Firestore is controlled by Firestore security rules and tenant isolation.
- The actual secret version is created via the Secret Manager API, not via Terraform.
- Terraform only manages the secret container (metadata, replication, rotation).

### Version Management

Secret Manager supports multiple versions per secret:
- Each time a value is set, a new version is created.
- Old versions are retained and accessible by version number.
- The `version_aliases` field provides human-readable aliases for version numbers (e.g., `{"prod": "5", "staging": "3"}`).
- The platform currently tracks only the current value, not historical versions.

## Rotation Configuration

The `rotation_period` field configures automatic rotation reminders:

| Field | TF Argument | Example | Description |
|-------|-------------|---------|-------------|
| rotation_period | `rotation.rotation_period` | `"7776000s"` (90 days) | Interval between rotation notifications |

**Note:** Terraform's `rotation` block supports both `rotation_period` and `next_rotation_time`. The current Pydantic model only captures `rotation_period`. Adding a rotation notification topic (Pub/Sub) is also supported at the GCP level but not modeled.

## Expiration

Two fields control secret expiration:

| Field | TF Argument | Description | Interaction |
|-------|-------------|-------------|-------------|
| expire_time | `expire_time` | Absolute expiration (RFC3339 timestamp) | Mutually exclusive with ttl |
| ttl | `ttl` | Relative expiration from creation (duration string) | Mutually exclusive with expire_time |

When a secret expires, it is automatically deleted by GCP. The platform should surface expiration dates to users and warn when secrets are approaching expiration.

## Integration Points

### Volume Mounts

Cloud Run services can mount secrets as files:

```yaml
# CloudRunVolume with secret
volumes:
  - name: my-secret-vol
    secret:
      secret: "node:my-secret"  # Reference to secret_manager node
      items:
        - version: "latest"
          path: "secret.txt"
```

### Environment Variables

Cloud Run and Cloud Function can reference secrets as environment variables:

```yaml
# EnvVarEntry with type="secret"
env_vars:
  - name: API_KEY
    type: secret
    secret: "node:my-secret"  # Reference to secret_manager node
    version: "latest"
```

### Third-Party API References

The `third_party_api` node type has a `secret_ref` field that can reference a secret_manager node to indicate where an API key is stored.

### Deploy Ordering

Secrets must be deployed BEFORE compute resources that reference them. The platform infers this dependency from:
- Volume mount secret references
- Environment variable secret references
- Explicit `depends_on` edges

## Terraform Template Details

The `secret_manager.tf.j2` template generates:

1. **Secret resource** with:
   - `secret_id` (defaults to node name)
   - `labels` (if any)
   - `expire_time` / `ttl` (if set)
   - `version_aliases` (if any)
   - `rotation` block (if rotation_period set)
   - `replication` block (auto or user_managed based on config)

2. **No secret version resources** -- values are managed via the platform, not Terraform.

3. **No IAM bindings in template** -- IAM for secrets is handled separately (Phase 6 will auto-infer `roles/secretmanager.secretAccessor` for SAs that need access).

## Fields Not in Current Model

The GCP Secret Manager API supports additional fields not currently in the Pydantic model:

| Field | Description | Why Not Modeled |
|-------|-------------|----------------|
| topics | Pub/Sub topics for rotation notifications | Low priority, can be added later |
| annotations | Key-value metadata | Not exposed in current UX |
| customer_managed_encryption | CMEK config | Enterprise feature, not needed for MVP |

---

*References: [01-security-template.md](01-security-template.md), [02-security-patterns.md](02-security-patterns.md)*
*Phase: 01-resource-node-specifications*
