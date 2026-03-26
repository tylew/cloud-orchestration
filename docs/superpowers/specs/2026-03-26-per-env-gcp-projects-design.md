# Per-Environment GCP Projects & Unified Env Vars

**Date:** 2026-03-26
**Status:** Draft
**Scope:** `packages/` (backend only, no frontend changes)

## Problem

All environments share one GCP project. Provisioning creates a single project, and all envs deploy Terraform to the same project with the same state bucket. This contradicts the intended architecture where different envs are different GCP projects.

Additionally, compute node environment configuration is split across multiple fields (`env`, `secrets`, `secret_environment_variables`) making it harder to reason about and manage during promotion.

## Goals

1. Each environment gets its own GCP project, provisioned on-demand when the user adds the env.
2. Unify compute node env vars into a single field where each entry is either a freeform value or a secret reference.
3. Basic blueprint promotion flow — copy blueprint from source env to target env, strip env var values (keep keys only).

## Non-Goals

- Smart secret copying/mirroring across envs (future)
- Env var value copying or inheritance (future)
- Env-specific networking or region overrides beyond per-env region field (future)
- Frontend changes
- Backward compatibility or migration for old env/secrets schema fields

---

## Design

### 1. Environment Data Model

The environment entry in the project doc expands to include GCP project details and provisioning state.

**Current:**
```python
{
    "id": "uuid",
    "name": "dev",
    "order": 0,
    "deployed": False,
    "deployed_at": None,
}
```

**New:**
```python
{
    "id": "uuid",
    "name": "dev",
    "order": 0,
    "deployed": False,
    "deployed_at": None,
    "gcp_project_id": "myapp-dev-a1b2c3",
    "tf_bucket": "myapp-dev-a1b2c3-tfstate",
    "region": "us-central1",
    "provision_status": "ready",   # pending | provisioning | ready | failed
    "provision_id": "abc123",
}
```

**Project doc changes:**
- Remove top-level `project_id` and `tf_bucket` fields. These now live on each environment entry.
- Existing projects: the current `project_id`/`tf_bucket` values belong to the dev env entry. No automated migration — clean break.

### 2. Unified Env Var Model

A single `EnvVarEntry` model replaces the split `env`/`secrets`/`secret_environment_variables` fields on compute node configs.

```python
class EnvVarEntry(BaseModel):
    name: str                          # env var name (e.g. DATABASE_URL)
    type: Literal["value", "secret"]   # what provides the value
    value: str | None = None           # for type="value"
    secret: str | None = None          # secret name, for type="secret"
    version: str = "latest"            # secret version, for type="secret"

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "value" and self.secret is not None:
            raise ValueError("type='value' entries must not set 'secret'")
        if self.type == "secret" and self.value is not None:
            raise ValueError("type='secret' entries must not set 'value'")
        return self
```

**Applied to compute configs:**

- `CloudRunConfig`: remove `env: list[CloudRunEnvVar]` and `secrets: list[CloudRunSecret]`. Add `env_vars: list[EnvVarEntry] = []`.
- `CloudFunctionConfig`: remove `env: list[CfEnvVar]`, `secrets: list[CloudRunSecret]`, and `secret_environment_variables: list[CfSecretEnvVar]`. Add `env_vars: list[EnvVarEntry] = []`.

Remove the old model classes (`CloudRunEnvVar`, `CloudRunSecret`, `CfEnvVar`, `CfSecretEnvVar`) entirely. No backward compatibility layer.

Note: `CfSecretEnvVar` / `secret_environment_variables` is defined on the `CloudFunctionConfig` model but is not rendered by the current Jinja2 template (which uses `config.secrets` instead). Removing it is safe — no functionality is lost.

### 3. Per-Env Provisioning

**New endpoint:** `POST /projects/{project_ref_id}/envs`

```python
class AddEnvRequest(BaseModel):
    name: str        # e.g. "staging"
    region: str = "" # defaults to first env's region if empty
```

**Flow:**

1. Validate: max 3 envs, name unique within project, name is kebab-case.
2. Generate GCP project ID via `generate_unique_project_id(display_name, environment=env_name)`. Note: the `environment` parameter now refers to the user's logical env name (e.g., "staging"), not the platform's `ENVIRONMENT` env var. This changes the GCP project ID naming scheme.
3. Add environment entry to project doc with `provision_status: "provisioning"`.
4. Create provision tracking record.
5. Run provisioning in background (same steps as today: create GCP project, enable APIs, create TF state bucket, setup Firebase, verify health).
6. On success: update env entry to `provision_status: "ready"`.
7. On failure: update env entry to `provision_status: "failed"`.

**Deploy guard:** Deploy endpoint checks `provision_status == "ready"` before allowing deploy. Returns 409 if still provisioning, 422 if failed.

**Failed env cleanup:** An env with `provision_status: "failed"` can be removed via the existing project settings update endpoint (which allows env removal for non-deployed envs).

**Initial provisioning:** The existing `POST /projects/provision` endpoint continues to create the first "dev" environment. The new `POST /projects/{ref}/envs` endpoint is only for adding subsequent environments. The refactoring adds `gcp_project_id`, `tf_bucket`, `region`, and `provision_status` fields to the dev env entry created during initial provisioning.

### 4. Blueprint Promotion

**New endpoint:** `POST /projects/{project_ref_id}/envs/{target_env}/promote`

```python
class PromoteRequest(BaseModel):
    source_env: str  # e.g. "dev"
```

**Flow:**

1. Validate: source env exists, target env exists, target env is provisioned (`provision_status == "ready"`).
2. Read all nodes from `blueprints/{source_env}/nodes/*`.
3. For each node, copy as-is except for compute nodes (Cloud Run, Cloud Function) where `env_vars` are stripped:
   - `type="value"` entries: keep `name` and `type`, clear `value` to `None`.
   - `type="secret"` entries: keep `name` and `type`, clear `secret` to `None`, reset `version` to `"latest"`.
4. Write all nodes to `blueprints/{target_env}/nodes/*` (full overwrite — deletes existing nodes first).
5. Write/update the blueprint parent doc at `blueprints/{target_env}` with metadata: `promoted_from`, `promoted_at`.
6. Log activity: "Promoted blueprint from {source} to {target}".

**Overwrite behavior:** Promotion replaces the target env's blueprint entirely. Any existing env var values configured in the target env are lost. No merge logic.

**No deploy gating:** Promotion does not require the source env to be deployed. Users can promote draft blueprints.

**Response schema:**
```python
{
    "nodes_copied": int,
    "nodes_deleted": int,
    "promoted_from": str,
    "promoted_at": str,
}
```

### 5. Terraform Generator & Template Changes

The generator currently reads `env` and `secrets` separately to emit Terraform blocks. It will read `env_vars` instead:

- `type="value"` → emits standard `env { name = "...", value = "..." }` block
- `type="secret"` → emits `env { name = "...", value_source { secret_key_ref { secret = "...", version = "..." } } }` block (Cloud Run) or the equivalent `secret_environment_variables` block (Cloud Functions)

**Jinja2 template changes:** The templates `cloud_run.tf.j2`, `cloud_function.tf.j2`, and `cloud_run_job.tf.j2` currently iterate `config.env` and `config.secrets` separately. These must be rewritten to iterate `config.env_vars` and branch on `entry.type`:

- Replace `{% for e in config.env %}` loops with `{% for e in config.env_vars if e.type == "value" %}`
- Replace `{% for s in config.secrets %}` loops with `{% for e in config.env_vars if e.type == "secret" %}`
- Update attribute access: the old `CloudRunSecret` used `env_name` for the env var name; `EnvVarEntry` uses `name`

### 6. Deploy Orchestrator Changes

`_run_deploy()` currently receives `project_id` and `tf_bucket` from the project doc's top-level fields.

**New flow:**
1. Look up the target environment entry by `env_name` in the project doc's `environments` array.
2. Read `gcp_project_id` and `tf_bucket` from that entry.
3. Check `provision_status == "ready"` — fail deploy if not.
4. Pass env-specific `gcp_project_id`, `tf_bucket`, and `region` to `submit_terraform_build()`.

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `packages/core/schemas/configs/env_vars.py` | `EnvVarEntry` model |
| `packages/api/handlers/promote.py` | Blueprint promotion endpoint |

### Modified Files

| File | Changes |
|------|---------|
| `packages/core/schemas/configs/cloud_run.py` | Remove `env`, `secrets`, `CloudRunEnvVar`, `CloudRunSecret`. Add `env_vars: list[EnvVarEntry]`. |
| `packages/core/schemas/configs/cloud_function.py` | Remove `env`, `secrets`, `secret_environment_variables`, `CfEnvVar`, `CfSecretEnvVar`. Add `env_vars: list[EnvVarEntry]`. |
| `packages/core/terraform/generator.py` | Read `env_vars` instead of `env` + `secrets`. Emit appropriate TF blocks by type. |
| `packages/core/terraform/templates/cloud_run.tf.j2` | Replace `config.env`/`config.secrets` loops with `config.env_vars` branching on type. |
| `packages/core/terraform/templates/cloud_function.tf.j2` | Replace `config.env`/`config.secrets` loops with `config.env_vars` branching on type. |
| `packages/core/terraform/templates/cloud_run_job.tf.j2` | Replace `config.env`/`config.secrets` loops with `config.env_vars` branching on type. |
| `packages/platform/store/projects.py` | Remove `project_id`/`tf_bucket` immutability checks. Add `get_env_entry()`, `add_environment()`, `update_env_provision_status()`. |
| `packages/api/handlers/provision.py` | Refactor: initial provisioning sets env-level fields. New `POST /projects/{ref}/envs` endpoint for adding envs. |
| `packages/api/handlers/projects.py` | Deploy initiation (`deploy_env`): read `gcp_project_id`, `tf_bucket`, `region` from target env entry instead of top-level project fields. Add provisioning guard. |
| `packages/platform/deploy_orchestrator.py` | Resolve GCP project details from environment entry, not project doc. |

### Removed Models

- `CloudRunEnvVar` (cloud_run.py)
- `CloudRunSecret` (cloud_run.py)
- `CfEnvVar` (cloud_function.py)
- `CfSecretEnvVar` (cloud_function.py)

Note: `CloudRunSecret` is imported by `cloud_function.py` for its `secrets` field. Both usages are removed.

---

## Risks

- **Existing blueprints break**: Blueprints stored with old `env`/`secrets` fields won't validate against the new schema. This is accepted — clean break, no migration.
- **TF generator correctness**: Cloud Run and Cloud Functions have different Terraform syntax for secret env vars. The generator must handle both correctly from the unified model.
- **Provisioning failures**: Adding an env triggers real GCP project creation. If it fails, the env is stuck in "failed" state. Need a retry mechanism or manual cleanup path (out of scope for v1, but the provision status field supports it).
