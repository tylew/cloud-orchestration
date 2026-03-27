# Security/Identity Category: Shared Patterns

**Category:** Security / Identity
**Types:** service_account, secret_manager
**Archetype:** Simple CRUD

---

## IAM Scope Differences

The two security types have fundamentally different IAM roles:

### Service Account -- The Identity Provider

- **iam_scope:** None in REGISTRY. Service accounts do not have IAM bindings ON them -- they ARE the identity.
- A service account is the "actor" in IAM. Other resources (Cloud Run, Cloud Functions, etc.) run AS a service account.
- The `roles` field on ServiceAccountConfig is platform metadata that tracks what GCP roles this SA should be granted. These roles are granted AT the project or resource level, not on the SA itself.
- The `service_account.tf.j2` template generates `google_project_iam_member` resources from the roles list, binding the SA to project-level roles.

### Secret Manager -- The Protected Resource

- **iam_scope:** `"resource"` in REGISTRY.
- **iam_terraform_resource:** `google_secret_manager_secret_iam_member`
- Secrets are protected resources. Other identities (service accounts) need IAM permissions to access them.
- Common role: `roles/secretmanager.secretAccessor` -- allows reading secret versions.
- IAM bindings are typically auto-inferred from the dependency graph: if a Cloud Run service mounts a secret volume, the service's SA needs `secretAccessor` on that secret.

### Summary

| Type | IAM Role | Who Acts | What's Protected |
|------|----------|----------|-----------------|
| service_account | Identity (actor) | The SA itself | N/A -- it grants access TO other resources |
| secret_manager | Resource (target) | SAs that need access | The secret value |

## Service Account Roles Field

The `roles` field on `ServiceAccountConfig` deserves special attention:

- It is a **platform-level metadata field**, not a Terraform argument on `google_service_account`.
- It stores the INTENDED role bindings for this SA as `list[IamRole]`.
- Each `IamRole` has: `role` (e.g., "roles/cloudsql.client"), `resource` (target node or blank for project-level), `description`.
- The current `service_account.tf.j2` template generates `google_project_iam_member` resources directly from this list.
- Full IAM binding generation (including resource-level bindings inferred from the dependency graph) is deferred to Phase 6.

**Key insight:** The roles field represents the user's EXPLICIT role assignments. Phase 6 will add AUTO-INFERRED roles from the dependency graph (e.g., a Cloud Run service that reads from Firestore should automatically get `roles/datastore.user` on its SA). The explicit roles in this field will coexist with auto-inferred roles.

## Secret Value Lifecycle

Secret Manager has a dual lifecycle:

### Terraform-Managed (the Secret Resource)

Terraform creates and manages the `google_secret_manager_secret` resource:
- Creates the secret container with replication config, labels, rotation settings.
- Does NOT manage secret versions (the actual values).
- Destroying the TF resource deletes the entire secret including all versions.

### Platform-Managed (the Secret Value)

The actual secret value is managed by the platform, not Terraform:
- The `value` field stores the secret data in Firestore (or is set via the Secret Manager API).
- The `value_provided` boolean tracks whether the value has been set.
- The `pending_email` field supports a UX workflow: mark a secret as "value needed" and assign someone to provide it.

### Why This Separation?

1. **Security:** Secret values should never appear in Terraform state files. TF state is stored in GCS and could be accessed by anyone with bucket permissions.
2. **Workflow:** Secret values often come from different people (e.g., a third-party API key from a vendor, a database password from a DBA). The pending_email flow supports this.
3. **Versioning:** Secret Manager supports multiple versions. The platform currently tracks only the current value, but the version_aliases field provides a mapping.

## Deletion Protection Considerations

### Service Account Deletion

- Deleting a service account immediately revokes all its permissions.
- Any compute resources running as this SA will lose access to GCP APIs.
- The platform should warn if the SA is referenced by any compute node's `service_account` field before allowing deletion.

### Secret Manager Deletion

- Secrets can have active versions that must be explicitly destroyed before the secret itself can be deleted (depending on GCP configuration).
- The platform should warn if the secret is referenced by any compute node's volume mounts or env vars before allowing deletion.
- `expire_time` and `ttl` fields can cause automatic secret expiration -- the platform should surface these to users.

## Foundational Type Dependencies

Both security types are foundational -- they are referenced by other resource types:

### Service Account References

- Every compute type has a `service_account` field (error-level required) that should reference a `service_account` node.
- This creates an implicit deploy ordering dependency: service accounts must be deployed before compute resources.
- The validation module checks that `iam.service_account` references point to valid `service_account` nodes.

### Secret Manager References

- Cloud Run volumes can mount secrets via `CloudRunVolumeSecret`.
- Cloud Run env vars can reference secrets via `EnvVarEntry` with `type="secret"`.
- Cloud Function secret volumes use `CfSecretVolume`.
- The `third_party_api` node type has a `secret_ref` field that can reference a secret_manager node.
- These references create deploy ordering dependencies: secrets must exist before compute resources that reference them.

---

*References: [01-security-template.md](01-security-template.md), [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md)*
*Phase: 01-resource-node-specifications*
