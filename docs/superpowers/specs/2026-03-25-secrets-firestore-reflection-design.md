# Secrets Firestore Reflection Design

**Date:** 2026-03-25
**Goal:** Add a Firestore reflection of Secret Manager state so the frontend can subscribe to secrets in real-time, while GCP Secret Manager remains the actual secret storage. Secret values never touch Firestore.

**Approach:** Firestore-first with GCP SM backing. Every secret mutation writes metadata to Firestore, then the actual value to GCP Secret Manager, then updates Firestore with the result. Firestore is the read path for the frontend; GCP SM is the value store.

---

## 1. Firestore Data Model

### Secret Document

**Path:** `tenants/{tid}/projects/{pid}/blueprints/{env}/secrets/{secretId}`

```json
{
  "secret_id": "db-password",
  "description": "Production database password",
  "created_at": "2026-03-25T...",
  "created_by": "tyler@pl4m.com",
  "latest_version": "3",
  "active_version_count": 2,
  "status": "active",
  "masked_value": "sk-a...789",
  "gcp_secret_name": "projects/my-project/secrets/db-password"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `secret_id` | string | GCP Secret Manager secret ID |
| `description` | string | User-provided description |
| `created_at` | string (ISO) | Creation timestamp |
| `created_by` | string | Email of creator |
| `latest_version` | string | Latest version number (any status) |
| `active_version_count` | int | Count of non-destroyed versions |
| `status` | string | `"active"`, `"destroyed"` (all versions destroyed / secret deleted), or `"failed"` (GCP SM write failed during create) |
| `masked_value` | string or null | Masked preview of latest active version. `null` if value is under 6 chars or no active versions remain |
| `gcp_secret_name` | string | Full GCP resource name for reference |

### Version Document

**Path:** `.../secrets/{secretId}/versions/{versionNumber}`

```json
{
  "version": "3",
  "status": "active",
  "created_at": "2026-03-25T...",
  "created_by": "tyler@pl4m.com",
  "destroyed_at": null,
  "destroyed_by": null,
  "masked_value": "sk-a...789"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | GCP SM version number |
| `status` | string | `"active"` or `"destroyed"` |
| `created_at` | string (ISO) | Version creation timestamp |
| `created_by` | string | Email of creator |
| `destroyed_at` | string (ISO) or null | When this version was destroyed |
| `destroyed_by` | string or null | Email of who destroyed it |
| `masked_value` | string or null | Masked preview captured at creation. `null` if under 6 chars |

### Masking Rule

- Secrets **under 6 characters**: `masked_value` is `null` (frontend renders as `••••••`)
- Secrets **6+ characters**: Use existing `mask_secret_value()` (first 15%, last 10% visible, min 1 char each side)
- Masked value is computed once at write time and stored — never recomputed from the real value
- Firestore never stores or receives the plaintext value

### Parent Document Rollback

The parent secret doc's `masked_value` always reflects the **latest active version**. When the latest version is destroyed:
1. Find the previous active version (highest version number with `status: "active"`)
2. Set parent `masked_value` to that version's `masked_value`
3. If no active versions remain, set parent `masked_value` to `null`

---

## 2. API Routes

New env-scoped routes under the existing projects namespace. Replaces current `/api/secrets/{project_ref_id}/...` routes.

| Method | Route | Auth Role | Description |
|--------|-------|-----------|-------------|
| `GET` | `/api/projects/{pid}/envs/{env}/secrets` | viewer | List all secrets (Firestore read) |
| `POST` | `/api/projects/{pid}/envs/{env}/secrets` | editor | Create secret (Firestore + GCP SM) |
| `GET` | `/api/projects/{pid}/envs/{env}/secrets/{secretId}` | viewer | Get secret metadata + version list |
| `PUT` | `/api/projects/{pid}/envs/{env}/secrets/{secretId}` | editor | Add new version (Firestore + GCP SM) |
| `DELETE` | `/api/projects/{pid}/envs/{env}/secrets/{secretId}` | admin | Delete entire secret |
| `DELETE` | `/api/projects/{pid}/envs/{env}/secrets/{secretId}/versions/{ver}` | editor | Destroy specific version |
| `GET` | `/api/projects/{pid}/envs/{env}/secrets/{secretId}/versions` | viewer | List version history |

`{pid}` = `project_ref_id`, `{env}` = `env_name`.

**Create payload:** `{ "secret_id": "db-password", "value": "the-actual-secret", "description": "..." }`

**Add version payload:** `{ "value": "new-secret-value" }`

All routes use `require_project_access()` for authorization, consistent with existing blueprint/deploy routes.

---

## 3. Operation Flows

### Create Secret

1. Handler validates payload, calls `store.secrets.create_secret()`
2. Store writes Firestore secret doc: `status: "active"`, `latest_version: null`
3. Store calls `gcp.secret_manager.create_secret_with_value()` → GCP SM
4. On success: store writes version `1` subdoc, updates parent doc with `latest_version: "1"`, `active_version_count: 1`, `masked_value` (applying <6 char rule)
5. On GCP failure: store marks Firestore doc `status: "failed"`, returns error

### Add Version

1. Handler calls `store.secrets.add_version()`
2. Store calls `gcp.secret_manager.add_secret_version()` → GCP SM
3. On success: store writes new version subdoc, updates parent doc `latest_version`, increments `active_version_count`, updates `masked_value`
4. On GCP failure: no Firestore changes (version subdoc not written), error returned to caller

### Destroy Version

1. Handler calls `store.secrets.destroy_version()`
2. Store calls `gcp.secret_manager.destroy_secret_version()` → GCP SM
3. On success: store updates version subdoc: `status: "destroyed"`, `destroyed_at`, `destroyed_by`
4. Store recalculates parent doc: decrements `active_version_count`, rolls back `masked_value` to previous active version (or `null` if none remain)
5. On GCP failure: no Firestore changes, error returned to caller

### Delete Secret

1. Handler calls `store.secrets.delete_secret()`
2. Store calls `gcp.secret_manager.delete_secret()` → GCP SM (removes all versions)
3. On success: store marks all version subdocs `status: "destroyed"`, marks parent doc `status: "destroyed"`

### List Secrets (Frontend)

- Frontend subscribes to Firestore collection: `tenants/{tid}/projects/{pid}/blueprints/{env}/secrets`
- Real-time updates on any create, version, or destroy
- No GCP SM calls — Firestore is the read path

---

## 4. Files

### Create

| File | Responsibility |
|------|---------------|
| `packages/platform/store/secrets.py` | Firestore CRUD: `create_secret()`, `get_secret()`, `list_secrets()`, `add_version()`, `list_versions()`, `destroy_version()`, `delete_secret()` |

### Modify

| File | Change |
|------|--------|
| `packages/platform/gcp/secret_manager.py` | Add `destroy_secret_version()` function (GCP SM API call) |
| `packages/api/handlers/secrets.py` | Replace project-scoped routes with env-scoped routes under `/projects/{pid}/envs/{env}/secrets/...`. Thin handlers delegating to `store.secrets` |
| `packages/api/main.py` | Update secrets router registration for new route prefix |

### No Changes

| File | Reason |
|------|--------|
| `packages/core/schemas/configs/secret_manager.py` | Blueprint node config unchanged |
| `packages/core/terraform/templates/secret_manager.tf.j2` | TF generation unchanged |
| `packages/core/validation.py` | Secret validation rules unchanged |

### Tests

| File | Coverage |
|------|----------|
| `packages/tests/test_secrets_store.py` | Unit tests: masking logic, version fallback, <6 char rule |
| `packages/tests/integration/test_store_secrets.py` | Firestore CRUD: create, version, destroy, delete, list |
| `packages/tests/integration/test_api_secrets.py` | API endpoints: all 7 routes, auth roles, error cases |

---

## 5. Masking Implementation

Wrapper around existing `mask_secret_value()` that enforces the short-secret floor:

```python
def safe_mask(value: str) -> str | None:
    """Mask a secret value for Firestore storage. Returns None if too short to mask safely."""
    if len(value) < 6:
        return None
    return mask_secret_value(value)
```

- Called once at write time (create or add version)
- Stored in both the version subdoc and the parent secret doc
- `None` means the frontend should render `••••••`
- The real value only passes through memory during the API request — it goes to GCP SM and is never stored in Firestore

---

## 6. Future Considerations

- **Cross-environment secret copying:** Mechanism to copy secrets between environments (different GCP projects). Deferred — will need its own spec.
- **Event-driven sync:** If users start managing secrets outside the platform (gcloud CLI, GCP Console), add GCP SM audit log → Cloud Function → Firestore sync. Deferred — write-through is sufficient while the platform is the only writer.

---

## Success Criteria

- Frontend can subscribe to `blueprints/{env}/secrets` and see real-time updates
- Secret values never appear in Firestore (only masked previews)
- Secrets under 6 characters show no preview at all
- Version history preserved with soft deletes for destroyed versions
- All operations write to both Firestore and GCP SM in sequence with failure handling
- Existing blueprint node config (`SecretManagerConfig`) and Terraform generation unchanged
