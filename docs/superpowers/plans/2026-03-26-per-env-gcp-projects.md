# Per-Environment GCP Projects & Unified Env Vars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each environment gets its own GCP project (provisioned on-demand), compute node env vars are unified into a single field, and blueprints can be promoted between envs with env var keys copied but values stripped.

**Architecture:** Environment entries in the project doc expand to hold per-env GCP project IDs, TF buckets, regions, and provisioning state. A new `EnvVarEntry` model replaces split env/secrets fields on compute configs. The existing `promote_blueprint` function in `blueprints.py` is extended to strip env var values during promotion. Deploy reads GCP details from the target env entry rather than project-level fields.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI, Firestore, Jinja2 (TF templates), pytest

**Spec:** `docs/superpowers/specs/2026-03-26-per-env-gcp-projects-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `packages/core/schemas/configs/env_vars.py` | Create | `EnvVarEntry` Pydantic model with type-based validation |
| `packages/core/schemas/configs/cloud_run.py` | Modify | Remove `CloudRunEnvVar`, `CloudRunSecret`, `env`, `secrets` fields. Add `env_vars: list[EnvVarEntry]` |
| `packages/core/schemas/configs/cloud_run_job.py` | Modify | Remove `env`, `secrets` imports/fields. Add `env_vars: list[EnvVarEntry]` |
| `packages/core/schemas/configs/cloud_function.py` | Modify | Remove `CfEnvVar`, `CfSecretEnvVar`, `env`, `secrets`, `secret_environment_variables`. Add `env_vars: list[EnvVarEntry]` |
| `packages/core/terraform/templates/cloud_run.tf.j2` | Modify | Replace `config.env`/`config.secrets` loops with `config.env_vars` branched by type |
| `packages/core/terraform/templates/cloud_run_job.tf.j2` | Modify | Same as cloud_run.tf.j2 |
| `packages/core/terraform/templates/cloud_function.tf.j2` | Modify | Replace `config.env`/`config.secrets` loops with `config.env_vars` branched by type |
| `packages/platform/store/projects.py` | Modify | Remove `project_id`/`tf_bucket` immutability checks. Add `get_env_entry()`, `add_environment()`, `update_env_provision_status()` |
| `packages/platform/store/blueprints.py` | Modify | Update `promote_blueprint()` to strip env var values on compute nodes |
| `packages/api/handlers/provision.py` | Modify | Refactor initial provisioning for env-level fields. Add `POST /projects/{ref}/envs` endpoint |
| `packages/api/handlers/projects.py` | Modify | `deploy_env()`: read GCP details from env entry, add provisioning guard |
| `packages/platform/deploy_orchestrator.py` | Modify | Accept env-resolved GCP details |
| `packages/api/handlers/promote.py` | Create | `POST /projects/{ref}/envs/{target}/promote` endpoint |
| `packages/tests/test_env_vars.py` | Create | Unit tests for `EnvVarEntry` model |
| `packages/tests/test_terraform.py` | Modify | Add tests for env_vars in TF generation |
| `packages/tests/test_promotion.py` | Create | Unit tests for env var stripping during promotion |
| `packages/tests/conftest.py` | Modify | Add fixtures with env_vars |

---

### Task 1: Create EnvVarEntry Model

**Files:**
- Create: `packages/core/schemas/configs/env_vars.py`
- Create: `packages/tests/test_env_vars.py`

- [ ] **Step 1: Write failing tests for EnvVarEntry**

```python
# packages/tests/test_env_vars.py
"""Tests for the unified EnvVarEntry model."""

import pytest
from pydantic import ValidationError


class TestEnvVarEntry:
    def test_value_type_valid(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="LOG_LEVEL", type="value", value="debug")
        assert entry.name == "LOG_LEVEL"
        assert entry.type == "value"
        assert entry.value == "debug"
        assert entry.secret is None

    def test_secret_type_valid(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="DB_URL", type="secret", secret="db-url")
        assert entry.name == "DB_URL"
        assert entry.type == "secret"
        assert entry.secret == "db-url"
        assert entry.version == "latest"
        assert entry.value is None

    def test_secret_type_with_version(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="DB_URL", type="secret", secret="db-url", version="3")
        assert entry.version == "3"

    def test_value_type_rejects_secret_field(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        with pytest.raises(ValidationError, match="must not set 'secret'"):
            EnvVarEntry(name="X", type="value", value="y", secret="bad")

    def test_secret_type_rejects_value_field(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        with pytest.raises(ValidationError, match="must not set 'value'"):
            EnvVarEntry(name="X", type="secret", secret="s", value="bad")

    def test_value_type_allows_none_value(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="EMPTY", type="value")
        assert entry.value is None

    def test_secret_type_allows_none_secret(self):
        from packages.core.schemas.configs.env_vars import EnvVarEntry
        entry = EnvVarEntry(name="EMPTY", type="secret")
        assert entry.secret is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py -v`
Expected: FAIL with `ModuleNotFoundError` (module doesn't exist yet)

- [ ] **Step 3: Create EnvVarEntry model**

```python
# packages/core/schemas/configs/env_vars.py
"""Unified environment variable model for compute nodes."""

from typing import Literal

from pydantic import BaseModel, model_validator


class EnvVarEntry(BaseModel):
    name: str
    type: Literal["value", "secret"]
    value: str | None = None
    secret: str | None = None
    version: str = "latest"

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.type == "value" and self.secret is not None:
            raise ValueError("type='value' entries must not set 'secret'")
        if self.type == "secret" and self.value is not None:
            raise ValueError("type='secret' entries must not set 'value'")
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/schemas/configs/env_vars.py packages/tests/test_env_vars.py
git commit -m "feat: add unified EnvVarEntry model with type validation"
```

---

### Task 2: Update CloudRunConfig to Use EnvVarEntry

**Files:**
- Modify: `packages/core/schemas/configs/cloud_run.py`
- Modify: `packages/tests/conftest.py`

- [ ] **Step 1: Write failing test for CloudRunConfig with env_vars**

Add to `packages/tests/test_env_vars.py`:

```python
class TestCloudRunConfigEnvVars:
    def test_cloud_run_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        config = CloudRunConfig(
            image="gcr.io/test/image:latest",
            env_vars=[
                {"name": "LOG_LEVEL", "type": "value", "value": "debug"},
                {"name": "DB_URL", "type": "secret", "secret": "db-url"},
            ],
        )
        assert len(config.env_vars) == 2
        assert config.env_vars[0].type == "value"
        assert config.env_vars[1].type == "secret"

    def test_cloud_run_config_no_env_field(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        assert not hasattr(CloudRunConfig.model_fields, "env") or "env" not in CloudRunConfig.model_fields

    def test_cloud_run_config_no_secrets_field(self):
        from packages.core.schemas.configs.cloud_run import CloudRunConfig
        assert not hasattr(CloudRunConfig.model_fields, "secrets") or "secrets" not in CloudRunConfig.model_fields
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py::TestCloudRunConfigEnvVars -v`
Expected: FAIL (CloudRunConfig still has `env`/`secrets`, no `env_vars`)

- [ ] **Step 3: Update CloudRunConfig**

In `packages/core/schemas/configs/cloud_run.py`:

1. Add import: `from .env_vars import EnvVarEntry`
2. Remove `CloudRunEnvVar` class (lines 23-25)
3. Remove `CloudRunSecret` class (lines 28-30)
4. On `CloudRunConfig`: remove `env: list[CloudRunEnvVar] = []` (line 176) and `secrets: list[CloudRunSecret] = []` (line 177)
5. Add `env_vars: list[EnvVarEntry] = []` to `CloudRunConfig`

**Preserve these classes** — they are NOT env vars, they handle volume-mounted secrets and other concerns:
- `CloudRunVolumeSecret`, `CloudRunVolumeSecretItem`, `CloudRunEmptyDir`, `CloudRunVolume`, `CloudRunVolumeMount`
- `WorkflowSecretRef`, `WorkflowDbRef`, `WorkflowPubSubRef`, `WorkflowInvokeRef`, `WorkflowTaskDispatch`, `WorkflowDefinition`

- [ ] **Step 4: Update conftest fixtures to use env_vars instead of env/secrets**

In `packages/tests/conftest.py`, the `minimal_envelope_data` and `complex_envelope_data` fixtures have Cloud Run nodes. These don't currently set `env` or `secrets`, so no changes needed. But verify they still parse.

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run full test suite to check for breakage**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: Some tests may fail if they reference `CloudRunEnvVar` or `CloudRunSecret`. Fix those in the next steps.

- [ ] **Step 6: Commit**

```bash
git add packages/core/schemas/configs/cloud_run.py packages/tests/test_env_vars.py
git commit -m "feat: replace CloudRunConfig env/secrets with unified env_vars"
```

---

### Task 3: Update CloudRunJobConfig and CloudFunctionConfig

**Files:**
- Modify: `packages/core/schemas/configs/cloud_run_job.py`
- Modify: `packages/core/schemas/configs/cloud_function.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/tests/test_env_vars.py`:

```python
class TestCloudRunJobConfigEnvVars:
    def test_job_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_run_job import CloudRunJobConfig
        config = CloudRunJobConfig(
            image="gcr.io/test/image:latest",
            env_vars=[
                {"name": "BATCH_SIZE", "type": "value", "value": "100"},
            ],
        )
        assert len(config.env_vars) == 1

    def test_job_config_no_legacy_fields(self):
        from packages.core.schemas.configs.cloud_run_job import CloudRunJobConfig
        assert "env" not in CloudRunJobConfig.model_fields
        assert "secrets" not in CloudRunJobConfig.model_fields


class TestCloudFunctionConfigEnvVars:
    def test_function_config_accepts_env_vars(self):
        from packages.core.schemas.configs.cloud_function import CloudFunctionConfig
        config = CloudFunctionConfig(
            runtime="python312",
            entry_point="main",
            env_vars=[
                {"name": "API_KEY", "type": "secret", "secret": "api-key"},
            ],
        )
        assert len(config.env_vars) == 1
        assert config.env_vars[0].type == "secret"

    def test_function_config_no_legacy_fields(self):
        from packages.core.schemas.configs.cloud_function import CloudFunctionConfig
        assert "env" not in CloudFunctionConfig.model_fields
        assert "secrets" not in CloudFunctionConfig.model_fields
        assert "secret_environment_variables" not in CloudFunctionConfig.model_fields
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py::TestCloudRunJobConfigEnvVars packages/tests/test_env_vars.py::TestCloudFunctionConfigEnvVars -v`
Expected: FAIL

- [ ] **Step 3: Update CloudRunJobConfig**

In `packages/core/schemas/configs/cloud_run_job.py`:

1. Update the import from `cloud_run` to remove `CloudRunEnvVar, CloudRunSecret` but keep all other imports (`CloudRunVpcAccess, CloudRunVolume, CloudRunVolumeMount, CloudRunBinaryAuth, WorkflowDefinition`)
2. Add import: `from .env_vars import EnvVarEntry`
3. Replace `env: list[CloudRunEnvVar] = []` with `env_vars: list[EnvVarEntry] = []`
4. Remove `secrets: list[CloudRunSecret] = []`

- [ ] **Step 4: Update CloudFunctionConfig**

In `packages/core/schemas/configs/cloud_function.py`:

1. Update import from `cloud_run`: change `from .cloud_run import CloudRunSecret, WorkflowDefinition` to `from .cloud_run import WorkflowDefinition`
2. Add import: `from .env_vars import EnvVarEntry`
3. Remove `CfEnvVar` class
4. Remove `CfSecretEnvVar` class
5. Replace `env: list[CfEnvVar] = []`, `secrets: list[CloudRunSecret] = []`, `secret_environment_variables: list[CfSecretEnvVar] = []` with `env_vars: list[EnvVarEntry] = []`

- [ ] **Step 5: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_env_vars.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: May see TF generation failures (templates still reference old fields). That's expected — fixed in Task 4.

- [ ] **Step 7: Commit**

```bash
git add packages/core/schemas/configs/cloud_run_job.py packages/core/schemas/configs/cloud_function.py packages/tests/test_env_vars.py
git commit -m "feat: replace CloudRunJob and CloudFunction env/secrets with unified env_vars"
```

---

### Task 4: Update Terraform Templates

**Files:**
- Modify: `packages/core/terraform/templates/cloud_run.tf.j2`
- Modify: `packages/core/terraform/templates/cloud_run_job.tf.j2`
- Modify: `packages/core/terraform/templates/cloud_function.tf.j2`
- Modify: `packages/tests/test_terraform.py`

- [ ] **Step 1: Write failing test for TF generation with env_vars**

Add to `packages/tests/test_terraform.py`:

```python
class TestEnvVarsTerraform:
    def test_cloud_run_value_env_var(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-sa", "type": "service_account", "config": {"account_id": "my-sa"}},
                {"name": "my-svc", "type": "cloud_run", "config": {
                    "image": "gcr.io/test/img:latest",
                    "service_account": "my-sa",
                    "env_vars": [
                        {"name": "LOG_LEVEL", "type": "value", "value": "debug"},
                    ],
                }, "depends_on": ["my-sa"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        main = files["main.tf"]
        assert 'name  = "LOG_LEVEL"' in main
        assert 'value = "debug"' in main

    def test_cloud_run_secret_env_var(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-sa", "type": "service_account", "config": {"account_id": "my-sa"}},
                {"name": "my-secret", "type": "secret_manager", "config": {}},
                {"name": "my-svc", "type": "cloud_run", "config": {
                    "image": "gcr.io/test/img:latest",
                    "service_account": "my-sa",
                    "env_vars": [
                        {"name": "DB_URL", "type": "secret", "secret": "node:my-secret.secret_id"},
                    ],
                }, "depends_on": ["my-sa", "my-secret"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        main = files["main.tf"]
        assert 'name = "DB_URL"' in main
        assert "secret_key_ref" in main

    def test_cloud_function_value_env_var(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-sa", "type": "service_account", "config": {"account_id": "my-sa"}},
                {"name": "my-func", "type": "cloud_function", "config": {
                    "runtime": "python312",
                    "entry_point": "main",
                    "service_account": "my-sa",
                    "env_vars": [
                        {"name": "ENV", "type": "value", "value": "prod"},
                    ],
                }, "depends_on": ["my-sa"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        main = files["main.tf"]
        assert "environment_variables" in main
        assert "ENV" in main

    def test_cloud_function_secret_env_var(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-sa", "type": "service_account", "config": {"account_id": "my-sa"}},
                {"name": "my-secret", "type": "secret_manager", "config": {}},
                {"name": "my-func", "type": "cloud_function", "config": {
                    "runtime": "python312",
                    "entry_point": "main",
                    "service_account": "my-sa",
                    "env_vars": [
                        {"name": "API_KEY", "type": "secret", "secret": "node:my-secret.secret_id"},
                    ],
                }, "depends_on": ["my-sa", "my-secret"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        main = files["main.tf"]
        assert "secret_environment_variables" in main
        assert "API_KEY" in main
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_terraform.py::TestEnvVarsTerraform -v`
Expected: FAIL (templates still use old `config.env`/`config.secrets`)

- [ ] **Step 3: Update cloud_run.tf.j2**

Replace the env var and secrets loops (lines 50-67) with:

```jinja2
{% for e in config.env_vars if e.type == "value" %}
      env {
        name  = "{{ e.name }}"
        value = "{{ e.value }}"
      }
{% endfor %}

{% for e in config.env_vars if e.type == "secret" %}
      env {
        name = "{{ e.name }}"
        value_source {
          secret_key_ref {
            secret  = {{ resolve_ref(e.secret) if e.secret.startswith('node:') else '"' ~ e.secret ~ '"' }}
            version = "{{ e.version }}"
          }
        }
      }
{% endfor %}
```

- [ ] **Step 4: Update cloud_run_job.tf.j2**

Replace the env var and secrets loops (lines 47-64) with the same pattern as cloud_run.tf.j2 (same block structure — `env {}` inside `containers {}`).

- [ ] **Step 5: Update cloud_function.tf.j2**

Replace the env var block (lines 48-54) and secrets loop (lines 56-63) with:

```jinja2
{% set value_vars = config.env_vars | selectattr("type", "equalto", "value") | list %}
{% if value_vars %}
    environment_variables = {
{% for e in value_vars %}
      {{ e.name }} = "{{ e.value }}"
{% endfor %}
    }
{% endif %}

{% for e in config.env_vars if e.type == "secret" %}
    secret_environment_variables {
      key        = "{{ e.name }}"
      project_id = var.gcp_project_id
      secret     = {{ resolve_ref(e.secret) if e.secret.startswith('node:') else '"' ~ e.secret ~ '"' }}
      version    = "{{ e.version }}"
    }
{% endfor %}
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_terraform.py -v`
Expected: All tests PASS (including existing tests)

- [ ] **Step 7: Commit**

```bash
git add packages/core/terraform/templates/cloud_run.tf.j2 packages/core/terraform/templates/cloud_run_job.tf.j2 packages/core/terraform/templates/cloud_function.tf.j2 packages/tests/test_terraform.py
git commit -m "feat: update TF templates to use unified env_vars field"
```

---

### Task 5: Update Project Store for Per-Env Fields

**Files:**
- Modify: `packages/platform/store/projects.py`

- [ ] **Step 1: Write failing tests**

Create `packages/tests/test_project_env.py`:

```python
"""Unit tests for per-env project store helpers."""

import pytest


class TestGetEnvEntry:
    def test_finds_env_by_name(self):
        from packages.platform.store.projects import get_env_entry
        envs = [
            {"id": "1", "name": "dev", "gcp_project_id": "proj-dev"},
            {"id": "2", "name": "staging", "gcp_project_id": "proj-staging"},
        ]
        entry = get_env_entry(envs, "staging")
        assert entry["gcp_project_id"] == "proj-staging"

    def test_returns_none_for_missing_env(self):
        from packages.platform.store.projects import get_env_entry
        envs = [{"id": "1", "name": "dev"}]
        assert get_env_entry(envs, "prod") is None

    def test_returns_none_for_empty_list(self):
        from packages.platform.store.projects import get_env_entry
        assert get_env_entry([], "dev") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_project_env.py -v`
Expected: FAIL (function doesn't exist)

- [ ] **Step 3: Add get_env_entry to projects.py**

Add to `packages/platform/store/projects.py`:

```python
def get_env_entry(environments: list[dict], env_name: str) -> dict | None:
    """Find an environment entry by name from the environments list."""
    for env in environments:
        if isinstance(env, dict) and env.get("name") == env_name:
            return env
    return None
```

- [ ] **Step 4: Remove project_id/tf_bucket immutability checks**

In `update_project_settings()`, remove lines 92-93:

```python
    for field in ("project_id", "tf_bucket"):
        if field in updates and updates[field] != current.get(field):
            raise ValueError(f"Cannot change immutable field: {field}")
```

These fields no longer exist at the project level.

- [ ] **Step 5: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_project_env.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/platform/store/projects.py packages/tests/test_project_env.py
git commit -m "feat: add get_env_entry helper, remove project-level immutability checks"
```

---

### Task 6: Update Deploy Handler and Orchestrator for Per-Env GCP Details

**Files:**
- Modify: `packages/api/handlers/projects.py` (lines 70-130)
- Modify: `packages/platform/deploy_orchestrator.py`

- [ ] **Step 1: Update deploy_env in projects.py**

Replace the deploy record creation and background task section (lines 118-130) with:

```python
    # Resolve GCP details from environment entry
    from packages.platform.store.projects import get_env_entry
    env_entry = get_env_entry(envs, env_name)

    # Provisioning guard
    provision_status = env_entry.get("provision_status", "")
    if provision_status == "provisioning":
        raise HTTPException(status_code=409, detail=f"Environment '{env_name}' is still provisioning")
    if provision_status == "failed":
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' provisioning failed")
    if provision_status != "ready":
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' is not provisioned")

    gcp_project_id = env_entry.get("gcp_project_id", "")
    tf_bucket = env_entry.get("tf_bucket", "")
    region = env_entry.get("region", "us-central1")

    if not gcp_project_id:
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' has no GCP project ID")

    deploy_id = deploy_store.create_deploy_record(owner_uid, gcp_project_id, env_name, {
        "project_ref_id": project_ref_id,
        "region": region,
        "tf_bucket": tf_bucket,
    })

    background_tasks.add_task(
        _run_deploy,
        owner_uid, deploy_id, project_ref_id, gcp_project_id,
        env_name, region, tf_bucket,
    )

    return JSONResponse(status_code=202, content={"deploy_id": deploy_id, "status": "pending"})
```

- [ ] **Step 2: Verify deploy_orchestrator.py needs no changes**

`_run_deploy()` already receives `project_id`, `env_name`, `region`, `tf_bucket` as parameters — it doesn't read from the project doc directly. The signature stays the same; only the caller (projects.py) changes where the values come from. Confirm by reading `deploy_orchestrator.py` line 20-21.

- [ ] **Step 3: Run unit tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/handlers/projects.py
git commit -m "feat: deploy reads GCP details from env entry, adds provisioning guard"
```

---

### Task 7: Update Provisioning for Per-Env Fields

**Files:**
- Modify: `packages/api/handlers/provision.py`

- [ ] **Step 1: Update initial provisioning to set env-level fields**

In `_run_provisioning()`, update the `save_project()` call (lines 232-238) to include env-level GCP details on the dev environment entry:

```python
    import uuid as _uuid
    environments = [{
        "id": str(_uuid.uuid4()),
        "name": "dev",
        "order": 0,
        "deployed": False,
        "deployed_at": None,
        "gcp_project_id": project_id,
        "tf_bucket": tf_bucket,
        "region": region,
        "provision_status": "ready",
        "provision_id": provision_id,
    }]

    project_store.save_project(tenant_id, {
        "display_name": display_name,
        "region": region,
        "environments": environments,
    })
```

Also update the `environments` variable at line 57 (before background task) to include the new fields with `provision_status: "provisioning"`. Note: `provision_id` is not yet known at line 57 — set it to `""` initially, then update it after `provision_store.create_provision_record()` at line 78, similar to the pattern in Task 8 (`env_entry["provision_id"] = provision_id`).

And update the `config` dict (lines 71-77) to remove top-level `project_id` and `tf_bucket`.

- [ ] **Step 2: Run unit tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add packages/api/handlers/provision.py
git commit -m "feat: initial provisioning sets env-level GCP fields on dev environment"
```

---

### Task 8: Add Per-Env Provisioning Endpoint

**Files:**
- Modify: `packages/api/handlers/provision.py`

- [ ] **Step 1: Add AddEnvRequest model and endpoint**

Add to `packages/api/handlers/provision.py`:

```python
import re
import uuid as _uuid

class AddEnvRequest(BaseModel):
    name: str
    region: str = ""


@router.post("/{project_ref_id}/envs")
async def add_environment(project_ref_id: str, req: AddEnvRequest,
                          background_tasks: BackgroundTasks,
                          user: CurrentUser = Depends(get_current_user)):
    """Add a new environment to an existing project, triggering GCP project provisioning."""
    # Validate env name is kebab-case
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", req.name):
        raise HTTPException(status_code=422, detail="Environment name must be kebab-case")

    # Get project
    project = project_store.get_project(user.tenant_id, project_ref_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    envs = project.get("environments", [])

    # Max 3 envs
    if len(envs) >= 3:
        raise HTTPException(status_code=422, detail="Maximum 3 environments allowed")

    # Name unique
    if any(isinstance(e, dict) and e.get("name") == req.name for e in envs):
        raise HTTPException(status_code=409, detail=f"Environment '{req.name}' already exists")

    # Validate org config
    missing = []
    for var in ["ORG_ID", "BILLING_ACCOUNT", "TENANTS_FOLDER_ID"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise HTTPException(status_code=500, detail=f"Server misconfigured: missing {', '.join(missing)}")

    # Resolve region
    region = req.region or next(
        (e.get("region", "us-central1") for e in envs if isinstance(e, dict)),
        "us-central1",
    )

    display_name = project.get("display_name", "project")
    project_id, tf_bucket = generate_unique_project_id(display_name, environment=req.name)

    # Create env entry
    env_entry = {
        "id": str(_uuid.uuid4()),
        "name": req.name,
        "order": len(envs),
        "deployed": False,
        "deployed_at": None,
        "gcp_project_id": project_id,
        "tf_bucket": tf_bucket,
        "region": region,
        "provision_status": "provisioning",
        "provision_id": "",  # set after creating provision record
    }

    # Create provision record
    config = {
        "project_id": project_id,
        "display_name": display_name,
        "region": region,
        "env_name": req.name,
        "tf_bucket": tf_bucket,
    }
    provision_id = provision_store.create_provision_record(user.tenant_id, project_id, config)
    env_entry["provision_id"] = provision_id

    # Add env to project
    envs.append(env_entry)
    project_store.update_project_settings(user.tenant_id, project_ref_id, {"environments": envs})

    # Run provisioning in background
    background_tasks.add_task(
        _run_env_provisioning,
        user.tenant_id, provision_id, project_ref_id, req.name,
        project_id, display_name, region, user.is_admin, tf_bucket,
    )

    return JSONResponse(status_code=202, content={
        "provision_id": provision_id,
        "env_name": req.name,
        "gcp_project_id": project_id,
        "status": "provisioning",
    })
```

- [ ] **Step 2: Add _run_env_provisioning background task**

```python
def _run_env_provisioning(tenant_id: str, provision_id: str, project_ref_id: str,
                          env_name: str, project_id: str, display_name: str,
                          region: str, is_admin: bool, tf_bucket: str):
    """Background task that provisions a GCP project for a new environment."""
    tenants_folder_id = os.environ.get("TENANTS_FOLDER_ID", "")
    billing_account = os.environ.get("BILLING_ACCOUNT", "")

    try:
        # Get tenant folder
        tenant_data = tenant_store.get_tenant(tenant_id)
        folder_id = tenant_data.get("folder_id") if tenant_data else None

        # Create env subfolder
        if folder_id:
            provision_store.update_provision_status(tenant_id, provision_id, "creating_env_folder")
            try:
                env_folder_id = ensure_tenant_folder(
                    f"{tenant_id}-{env_name}", env_name, folder_id,
                )
                folder_id = env_folder_id
            except Exception as e:
                log.warning("Failed to create env subfolder: %s", e)

        # Create GCP project
        provision_store.update_provision_status(tenant_id, provision_id, "creating_project")
        gcp_result = create_gcp_project(
            project_id, display_name,
            billing_account=billing_account or None,
            folder_id=folder_id,
        )
        if not gcp_result.get("created") and not gcp_result.get("skipped"):
            _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name,
                                gcp_result.get("error", "Failed to create project"))
            return

        # Enable APIs
        provision_store.update_provision_status(tenant_id, provision_id, "enabling_apis")
        api_results = enable_apis(project_id)
        failed_apis = [a for a in api_results if not a["success"]]
        if failed_apis:
            _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name,
                                f"Failed to enable APIs: {', '.join(a['api'] for a in failed_apis)}")
            return

        # Create tfstate bucket
        provision_store.update_provision_status(tenant_id, provision_id, "creating_bucket")
        bucket_result = create_tf_state_bucket(project_id, region)
        if "error" in bucket_result:
            _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name, bucket_result["error"])
            return

        # Setup Firebase Auth
        provision_store.update_provision_status(tenant_id, provision_id, "setup_firebase")
        setup_firebase_auth(project_id)

        # Verify health
        provision_store.update_provision_status(tenant_id, provision_id, "verifying")
        verify_project_health(project_id)

        # Update env entry to ready
        _update_env_provision_status(tenant_id, project_ref_id, env_name, "ready")
        provision_store.update_provision_status(tenant_id, provision_id, "ready")

    except Exception as e:
        log.exception("Env provisioning failed for %s/%s", project_id, env_name)
        _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name, str(e))


def _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name, error):
    """Mark env provisioning as failed in both provision record and project env entry."""
    provision_store.update_provision_status(tenant_id, provision_id, "failed", error=error)
    _update_env_provision_status(tenant_id, project_ref_id, env_name, "failed")


def _update_env_provision_status(tenant_id, project_ref_id, env_name, status):
    """Update provision_status on a specific environment entry in the project doc."""
    project = project_store.get_project(tenant_id, project_ref_id)
    if not project:
        return
    envs = project.get("environments", [])
    for env in envs:
        if isinstance(env, dict) and env.get("name") == env_name:
            env["provision_status"] = status
            break
    project_store.update_project_settings(tenant_id, project_ref_id, {"environments": envs})
```

- [ ] **Step 3: Run unit tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/handlers/provision.py
git commit -m "feat: add POST /projects/{ref}/envs endpoint for per-env provisioning"
```

---

### Task 9: Update Blueprint Promotion to Strip Env Vars

**Files:**
- Modify: `packages/platform/store/blueprints.py`
- Create: `packages/tests/test_promotion.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/tests/test_promotion.py
"""Tests for blueprint promotion env var stripping."""

from packages.platform.store.blueprints import _strip_env_var_values


class TestStripEnvVarValues:
    def test_strips_value_entries(self):
        nodes = [
            {
                "name": "my-svc", "type": "cloud_run", "slug": "my-svc",
                "config": {
                    "image": "gcr.io/test/img",
                    "env_vars": [
                        {"name": "LOG_LEVEL", "type": "value", "value": "debug"},
                        {"name": "PORT", "type": "value", "value": "8080"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        env_vars = result[0]["config"]["env_vars"]
        assert len(env_vars) == 2
        assert env_vars[0]["name"] == "LOG_LEVEL"
        assert env_vars[0]["type"] == "value"
        assert env_vars[0].get("value") is None
        assert env_vars[1].get("value") is None

    def test_strips_secret_entries(self):
        nodes = [
            {
                "name": "my-svc", "type": "cloud_run", "slug": "my-svc",
                "config": {
                    "image": "gcr.io/test/img",
                    "env_vars": [
                        {"name": "DB_URL", "type": "secret", "secret": "db-url", "version": "3"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        env_vars = result[0]["config"]["env_vars"]
        assert env_vars[0]["name"] == "DB_URL"
        assert env_vars[0]["type"] == "secret"
        assert env_vars[0].get("secret") is None
        assert env_vars[0]["version"] == "latest"

    def test_non_compute_nodes_unchanged(self):
        nodes = [
            {
                "name": "my-vpc", "type": "vpc", "slug": "my-vpc",
                "config": {"auto_create_subnetworks": False},
            },
        ]
        result = _strip_env_var_values(nodes)
        assert result[0]["config"]["auto_create_subnetworks"] is False

    def test_mixed_nodes(self):
        nodes = [
            {"name": "my-vpc", "type": "vpc", "slug": "my-vpc", "config": {}},
            {
                "name": "my-func", "type": "cloud_function", "slug": "my-func",
                "config": {
                    "runtime": "python312",
                    "entry_point": "main",
                    "env_vars": [
                        {"name": "API_KEY", "type": "secret", "secret": "key"},
                    ],
                },
            },
        ]
        result = _strip_env_var_values(nodes)
        assert "env_vars" not in result[0]["config"]
        assert result[1]["config"]["env_vars"][0].get("secret") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_promotion.py -v`
Expected: FAIL (`_strip_env_var_values` doesn't exist)

- [ ] **Step 3: Add _strip_env_var_values to blueprints.py**

Add to `packages/platform/store/blueprints.py`:

```python
import copy

_COMPUTE_TYPES = frozenset({"cloud_run", "cloud_function", "cloud_run_job"})


def _strip_env_var_values(nodes: list[dict]) -> list[dict]:
    """Deep copy nodes, stripping env var values/secrets on compute nodes for promotion."""
    result = copy.deepcopy(nodes)
    for node in result:
        if node.get("type") not in _COMPUTE_TYPES:
            continue
        config = node.get("config", {})
        env_vars = config.get("env_vars", [])
        for entry in env_vars:
            if entry.get("type") == "value":
                entry["value"] = None
            elif entry.get("type") == "secret":
                entry["secret"] = None
                entry["version"] = "latest"
    return result
```

- [ ] **Step 4: Integrate into promote_blueprint**

Update `promote_blueprint()` in `blueprints.py` to call `_strip_env_var_values` before saving:

```python
def promote_blueprint(tenant_id: str, project_ref_id: str, source_env: str, target_env: str) -> dict:
    """Copy blueprint from source_env to target_env, stripping env var values on compute nodes."""
    source = get_env_blueprint(tenant_id, project_ref_id, source_env)
    if not source:
        raise ValueError(f"No blueprint found for env '{source_env}'")

    envelope = source.get("envelope", {})

    # Strip env var values on compute nodes
    original_nodes = envelope.get("nodes", [])
    envelope["nodes"] = _strip_env_var_values(original_nodes)

    # Delete all existing target subcollection docs
    client = get_client()
    target_ref = _project_ref(tenant_id, project_ref_id).collection("blueprints").document(target_env)
    target_nodes_coll = target_ref.collection("nodes")
    delete_ops = []
    for doc in target_nodes_coll.list_documents():
        delete_ops.append(lambda batch, r=doc: batch.delete(r))
    if delete_ops:
        _batch_commit(client, delete_ops)

    # Write target via save
    nodes_deleted = len(delete_ops)
    result = save_env_blueprint(tenant_id, project_ref_id, target_env, envelope)
    now = datetime.now(timezone.utc)

    # Update target parent with promotion metadata
    target_ref.update({
        "promoted_from": source_env,
        "promoted_at": now,
    })

    return {
        "nodes_copied": result["node_count"],
        "nodes_deleted": nodes_deleted,
        "promoted_from": source_env,
        "promoted_at": now.isoformat(),
    }
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/test_promotion.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add packages/platform/store/blueprints.py packages/tests/test_promotion.py
git commit -m "feat: strip env var values during blueprint promotion"
```

---

### Task 10: Create Promote API Handler

**Files:**
- Create: `packages/api/handlers/promote.py`

- [ ] **Step 1: Create promote handler**

```python
# packages/api/handlers/promote.py
"""Blueprint promotion endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import projects as project_store

log = logging.getLogger(__name__)

router = APIRouter()


class PromoteRequest(BaseModel):
    source_env: str


@router.post("/projects/{project_ref_id}/envs/{target_env}/promote")
async def promote_blueprint(project_ref_id: str, target_env: str, req: PromoteRequest,
                            access: ProjectAccess = Depends(require_project_access("editor"))):
    """Promote blueprint from source env to target env, stripping env var values."""
    project = access.project
    owner_uid = access.owner_uid
    envs = project.get("environments", [])

    # Validate source env exists
    source_entry = project_store.get_env_entry(envs, req.source_env)
    if not source_entry:
        raise HTTPException(status_code=404, detail=f"Source environment '{req.source_env}' not found")

    # Validate target env exists
    target_entry = project_store.get_env_entry(envs, target_env)
    if not target_entry:
        raise HTTPException(status_code=404, detail=f"Target environment '{target_env}' not found")

    # Validate target is provisioned
    provision_status = target_entry.get("provision_status", "")
    if provision_status != "ready":
        raise HTTPException(status_code=422, detail=f"Target environment '{target_env}' is not provisioned (status: {provision_status})")

    try:
        result = blueprint_store.promote_blueprint(owner_uid, project_ref_id, req.source_env, target_env)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Log activity
    from packages.platform.store.projects import add_activity
    add_activity(
        owner_uid, project_ref_id,
        action="promote",
        env=target_env,
        user_email=access.user.email,
        user_display_name=access.user.display_name,
        details={"source_env": req.source_env, "nodes_copied": result["nodes_copied"]},
    )

    return result
```

- [ ] **Step 2: Register router in main app**

In `packages/api/main.py`, add the import alongside other handler imports (around line 30) and register the router after line 62:

```python
from packages.api.handlers.promote import router as promote_router
# ... after line 62:
app.include_router(promote_router, prefix="/api")
```

The promote router uses `APIRouter()` with no prefix (same pattern as `projects.py`). The full route path is in the decorator: `/projects/{ref}/envs/{target}/promote`.

- [ ] **Step 3: Run unit tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration -x`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/handlers/promote.py
git commit -m "feat: add POST /projects/{ref}/envs/{target}/promote endpoint"
```

---

### Task 11: Final Integration Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full unit test suite**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && python -m pytest packages/tests/ -v --ignore=packages/tests/integration`
Expected: All PASS

- [ ] **Step 2: Verify no references to removed classes**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && grep -rn "CloudRunEnvVar\|CloudRunSecret\|CfEnvVar\|CfSecretEnvVar" packages/ --include="*.py" | grep -v __pycache__`
Expected: No matches (all references removed)

- [ ] **Step 3: Verify env_vars usage in templates**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && grep -n "config\.env\b\|config\.secrets\b" packages/core/terraform/templates/*.j2`
Expected: No matches (all templates updated)

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: clean up remaining references to legacy env var fields"
```
