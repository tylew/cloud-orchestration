# Secrets Firestore Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Firestore reflection of GCP Secret Manager state with env-scoped routes, version tracking, soft deletes, and masked values — so the frontend can subscribe to secrets in real-time.

**Architecture:** New `platform/store/secrets.py` owns Firestore CRUD. Existing `platform/gcp/secret_manager.py` gets one new function (`destroy_secret_version`). Handlers in `api/handlers/secrets.py` are replaced with env-scoped routes that delegate to the store module. The store module calls the GCP wrapper for actual secret operations.

**Tech Stack:** Python 3.12, FastAPI, Google Cloud Firestore, Google Cloud Secret Manager

---

## File Map

**Create:**
- `packages/platform/store/secrets.py` — Firestore CRUD for secret metadata + version tracking
- `packages/tests/test_secrets_masking.py` — Unit tests for safe_mask and version fallback logic
- `packages/tests/integration/test_store_secrets.py` — Firestore + GCP SM integration tests
- `packages/tests/integration/test_api_secrets.py` — API endpoint integration tests

**Modify:**
- `packages/platform/gcp/secret_manager.py` — Add `destroy_secret_version()` and `safe_mask()`
- `packages/api/handlers/secrets.py` — Replace with env-scoped routes
- `packages/api/main.py` — No change needed (router already registered at `/api` prefix; new routes use different paths within the same router)

---

### Task 1: Add `destroy_secret_version()` and `safe_mask()` to GCP wrapper

**Files:**
- Modify: `packages/platform/gcp/secret_manager.py`
- Create: `packages/tests/test_secrets_masking.py`

- [ ] **Step 1: Add `safe_mask()` function**

Append to `packages/platform/gcp/secret_manager.py`:

```python
def safe_mask(value: str) -> str | None:
    """Mask a secret value for Firestore storage. Returns None if too short to mask safely."""
    if len(value) < 6:
        return None
    return mask_secret_value(value)


def destroy_secret_version(project_id: str, secret_id: str, version: str) -> None:
    """Destroy a specific secret version in GCP Secret Manager."""
    client = _get_sm_client()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    client.destroy_secret_version(request={"name": name})
```

- [ ] **Step 2: Write masking unit tests**

Create `packages/tests/test_secrets_masking.py`:

```python
"""Unit tests for secret masking logic."""

from packages.platform.gcp.secret_manager import mask_secret_value, safe_mask


class TestSafeMask:
    def test_short_secret_returns_none(self):
        assert safe_mask("abc") is None
        assert safe_mask("12345") is None
        assert safe_mask("") is None

    def test_six_char_secret_returns_masked(self):
        result = safe_mask("abcdef")
        assert result is not None
        assert "..." in result

    def test_long_secret_shows_partial(self):
        result = safe_mask("sk-abc123xyz789longkey")
        assert result is not None
        assert result.startswith("sk-")
        assert "..." in result

    def test_exactly_threshold(self):
        # 6 chars is the boundary — should mask
        assert safe_mask("123456") is not None
        # 5 chars is under — should return None
        assert safe_mask("12345") is None


class TestMaskSecretValue:
    def test_short_value_returns_stars(self):
        assert mask_secret_value("abc") == "******"

    def test_long_value_preserves_ends(self):
        result = mask_secret_value("sk-abc123xyz789")
        assert result[0] == "s"
        assert "..." in result
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest packages/tests/test_secrets_masking.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/platform/gcp/secret_manager.py packages/tests/test_secrets_masking.py
git commit -m "feat: add safe_mask() and destroy_secret_version() to GCP SM wrapper"
```

---

### Task 2: Create Firestore store module for secrets

**Files:**
- Create: `packages/platform/store/secrets.py`

- [ ] **Step 1: Create the store module**

```python
"""Firestore CRUD for secret metadata and version tracking.

Secret values are NEVER stored in Firestore — only masked previews.
Actual values go to GCP Secret Manager via platform.gcp.secret_manager.
"""

import logging
from datetime import datetime, timezone

from packages.platform.store.client import get_client, _project_ref
from packages.platform.gcp import secret_manager as sm

log = logging.getLogger(__name__)


def _secrets_ref(tenant_id: str, project_ref_id: str, env_name: str):
    """Reference to the secrets subcollection under a blueprint environment."""
    return _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("secrets")


def _secret_ref(tenant_id: str, project_ref_id: str, env_name: str, secret_id: str):
    return _secrets_ref(tenant_id, project_ref_id, env_name).document(secret_id)


def _versions_ref(tenant_id: str, project_ref_id: str, env_name: str, secret_id: str):
    return _secret_ref(tenant_id, project_ref_id, env_name, secret_id) \
        .collection("versions")


def create_secret(tenant_id: str, project_ref_id: str, env_name: str,
                  project_id: str, secret_id: str, value: str,
                  description: str, user_email: str) -> dict:
    """Create a new secret in Firestore + GCP Secret Manager.

    Flow: write Firestore doc → create in GCP SM → write version subdoc → update parent.
    """
    now = datetime.now(timezone.utc).isoformat()
    doc_ref = _secret_ref(tenant_id, project_ref_id, env_name, secret_id)

    # Step 1: Write initial Firestore doc
    doc_ref.set({
        "secret_id": secret_id,
        "description": description,
        "created_at": now,
        "created_by": user_email,
        "latest_version": None,
        "active_version_count": 0,
        "status": "active",
        "masked_value": None,
        "gcp_secret_name": "",
    })

    # Step 2: Create in GCP Secret Manager
    try:
        result = sm.create_secret_with_value(project_id, secret_id, value)
    except Exception as e:
        doc_ref.update({"status": "failed"})
        raise

    # Step 3: Write version 1 subdoc
    masked = sm.safe_mask(value)
    version_num = result["version"].split("/")[-1]  # e.g. "projects/.../versions/1" → "1"
    _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version_num).set({
        "version": version_num,
        "status": "active",
        "created_at": now,
        "created_by": user_email,
        "destroyed_at": None,
        "destroyed_by": None,
        "masked_value": masked,
    })

    # Step 4: Update parent doc
    doc_ref.update({
        "latest_version": version_num,
        "active_version_count": 1,
        "masked_value": masked,
        "gcp_secret_name": result["secret_name"],
    })

    return {"secret_id": secret_id, "version": version_num, "status": "active"}


def add_version(tenant_id: str, project_ref_id: str, env_name: str,
                project_id: str, secret_id: str, value: str,
                user_email: str) -> dict:
    """Add a new version to an existing secret."""
    # GCP SM first — no Firestore changes on failure
    version_name = sm.add_secret_version(project_id, secret_id, value)

    now = datetime.now(timezone.utc).isoformat()
    masked = sm.safe_mask(value)
    version_num = version_name.split("/")[-1]

    # Write version subdoc
    _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version_num).set({
        "version": version_num,
        "status": "active",
        "created_at": now,
        "created_by": user_email,
        "destroyed_at": None,
        "destroyed_by": None,
        "masked_value": masked,
    })

    # Update parent doc
    doc_ref = _secret_ref(tenant_id, project_ref_id, env_name, secret_id)
    doc = doc_ref.get()
    current = doc.to_dict() if doc.exists else {}
    count = current.get("active_version_count", 0) + 1
    updates = {
        "latest_version": version_num,
        "active_version_count": count,
        "masked_value": masked,
    }
    # Revive empty secrets
    if current.get("status") == "empty":
        updates["status"] = "active"
    doc_ref.update(updates)

    return {"secret_id": secret_id, "version": version_num}


def destroy_version(tenant_id: str, project_ref_id: str, env_name: str,
                    project_id: str, secret_id: str, version: str,
                    user_email: str) -> dict:
    """Destroy a specific version (soft delete in Firestore, real destroy in GCP SM)."""
    # GCP SM first — no Firestore changes on failure
    sm.destroy_secret_version(project_id, secret_id, version)

    now = datetime.now(timezone.utc).isoformat()

    # Soft delete version subdoc
    ver_ref = _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version)
    ver_ref.update({
        "status": "destroyed",
        "destroyed_at": now,
        "destroyed_by": user_email,
    })

    # Recalculate parent doc
    _recalculate_parent(tenant_id, project_ref_id, env_name, secret_id)

    return {"secret_id": secret_id, "version": version, "status": "destroyed"}


def delete_secret(tenant_id: str, project_ref_id: str, env_name: str,
                  project_id: str, secret_id: str) -> dict:
    """Delete entire secret from GCP SM, mark as destroyed in Firestore."""
    # GCP SM first
    sm.delete_secret(project_id, secret_id)

    now = datetime.now(timezone.utc).isoformat()

    # Mark all versions as destroyed
    versions_coll = _versions_ref(tenant_id, project_ref_id, env_name, secret_id)
    for doc in versions_coll.stream():
        doc.reference.update({"status": "destroyed", "destroyed_at": now})

    # Mark parent as destroyed
    _secret_ref(tenant_id, project_ref_id, env_name, secret_id).update({
        "status": "destroyed",
        "active_version_count": 0,
        "masked_value": None,
    })

    return {"secret_id": secret_id, "status": "destroyed"}


def get_secret(tenant_id: str, project_ref_id: str, env_name: str,
               secret_id: str) -> dict | None:
    """Get secret metadata from Firestore (no GCP SM call)."""
    doc = _secret_ref(tenant_id, project_ref_id, env_name, secret_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def list_secrets(tenant_id: str, project_ref_id: str, env_name: str) -> list[dict]:
    """List all secrets for an environment from Firestore."""
    results = []
    for doc in _secrets_ref(tenant_id, project_ref_id, env_name).stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def list_versions(tenant_id: str, project_ref_id: str, env_name: str,
                  secret_id: str) -> list[dict]:
    """List all versions for a secret from Firestore."""
    results = []
    for doc in _versions_ref(tenant_id, project_ref_id, env_name, secret_id).stream():
        data = doc.to_dict()
        results.append(data)
    # Sort by version number descending
    results.sort(key=lambda v: int(v.get("version", "0")), reverse=True)
    return results


def _recalculate_parent(tenant_id: str, project_ref_id: str, env_name: str,
                        secret_id: str) -> None:
    """Recalculate parent doc fields after a version status change."""
    versions = list_versions(tenant_id, project_ref_id, env_name, secret_id)
    active = [v for v in versions if v.get("status") == "active"]
    count = len(active)

    # Latest active version's masked value (versions are sorted descending)
    masked = active[0].get("masked_value") if active else None

    updates: dict = {
        "active_version_count": count,
        "masked_value": masked,
    }
    if count == 0:
        updates["status"] = "empty"

    _secret_ref(tenant_id, project_ref_id, env_name, secret_id).update(updates)
```

- [ ] **Step 2: Commit**

```bash
git add packages/platform/store/secrets.py
git commit -m "feat: add Firestore store module for secrets with version tracking"
```

---

### Task 3: Replace API handlers with env-scoped routes

**Files:**
- Modify: `packages/api/handlers/secrets.py`

- [ ] **Step 1: Replace handlers**

Replace the full contents of `packages/api/handlers/secrets.py` with:

```python
"""Secret management endpoints — env-scoped with Firestore reflection."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import secrets as secret_store

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets")
async def list_secrets(
    project_ref_id: str, env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all secrets for an environment (Firestore read)."""
    secrets = secret_store.list_secrets(access.owner_uid, project_ref_id, env_name)
    return {"secrets": secrets}


@router.post("/projects/{project_ref_id}/envs/{env_name}/secrets")
async def create_secret(
    project_ref_id: str, env_name: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Create a new secret (Firestore + GCP Secret Manager)."""
    secret_id = payload.get("secret_id", "").strip()
    value = payload.get("value", "")
    description = payload.get("description", "")

    if not secret_id:
        raise HTTPException(status_code=422, detail="secret_id is required")
    if not value:
        raise HTTPException(status_code=422, detail="value is required")

    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.create_secret(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, value, description,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to create secret %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not create secret: {e}")


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def get_secret(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Get secret metadata + version list."""
    secret = secret_store.get_secret(access.owner_uid, project_ref_id, env_name, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail=f"Secret '{secret_id}' not found")
    versions = secret_store.list_versions(access.owner_uid, project_ref_id, env_name, secret_id)
    return {**secret, "versions": versions}


@router.put("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def add_version(
    project_ref_id: str, env_name: str, secret_id: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Add a new version to an existing secret."""
    value = payload.get("value", "")
    if not value:
        raise HTTPException(status_code=422, detail="value is required")

    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.add_version(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, value,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to add version for %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not add version: {e}")


@router.delete("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def delete_secret(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("admin")),
):
    """Delete entire secret from GCP SM + mark destroyed in Firestore."""
    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.delete_secret(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id,
        )
        return result
    except Exception as e:
        log.warning("Failed to delete secret %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not delete secret: {e}")


@router.delete("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}/versions/{version}")
async def destroy_version(
    project_ref_id: str, env_name: str, secret_id: str, version: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Destroy a specific secret version (soft delete)."""
    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.destroy_version(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, version,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to destroy version %s/%s: %s", secret_id, version, e)
        raise HTTPException(status_code=500, detail=f"Could not destroy version: {e}")


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}/versions")
async def list_versions(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List version history for a secret."""
    versions = secret_store.list_versions(access.owner_uid, project_ref_id, env_name, secret_id)
    return {"versions": versions}
```

- [ ] **Step 2: Verify core tests still pass**

Run: `python -m pytest packages/tests/ -v --tb=short -m "not integration"`
Expected: All 45+ core tests PASS (handlers are only tested via integration tests).

- [ ] **Step 3: Commit**

```bash
git add packages/api/handlers/secrets.py
git commit -m "feat: replace project-scoped secret routes with env-scoped routes"
```

---

### Task 4: Integration tests — Firestore store

**Files:**
- Create: `packages/tests/integration/test_store_secrets.py`

- [ ] **Step 1: Write store integration tests**

```python
"""Integration tests for Firestore secrets store with GCP Secret Manager."""

import pytest
from packages.platform.store import secrets as secret_store

pytestmark = pytest.mark.integration


class TestSecretLifecycle:
    def test_create_and_read(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-sec"
        env_name = "dev"
        secret_id = f"{test_prefix}-secret"

        try:
            result = secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "my-secret-value-123456",
                "test secret", "test@test.com",
            )
            assert result["status"] == "active"
            assert result["version"] == "1"

            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret is not None
            assert secret["secret_id"] == secret_id
            assert secret["status"] == "active"
            assert secret["active_version_count"] == 1
            assert secret["masked_value"] is not None  # 22 chars > 6
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_add_version(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-ver"
        env_name = "dev"
        secret_id = f"{test_prefix}-versioned"

        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "initial-value-123456",
                "", "test@test.com",
            )
            result = secret_store.add_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "updated-value-654321",
                "test@test.com",
            )
            assert result["version"] == "2"

            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret["active_version_count"] == 2
            assert secret["latest_version"] == "2"
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_destroy_version_soft_delete(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-dst"
        env_name = "dev"
        secret_id = f"{test_prefix}-destroy"

        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "value-one-123456",
                "", "test@test.com",
            )
            secret_store.add_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "value-two-654321",
                "test@test.com",
            )

            # Destroy version 2
            result = secret_store.destroy_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "2",
                "test@test.com",
            )
            assert result["status"] == "destroyed"

            # Parent should reflect version 1 now
            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret["active_version_count"] == 1
            assert secret["status"] == "active"

            # Version 2 should be soft deleted
            versions = secret_store.list_versions(tenant_id, project_ref_id, env_name, secret_id)
            v2 = next(v for v in versions if v["version"] == "2")
            assert v2["status"] == "destroyed"
            assert v2["destroyed_by"] == "test@test.com"
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_destroy_last_version_sets_empty(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-emp"
        env_name = "dev"
        secret_id = f"{test_prefix}-empty"

        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "only-value-123456",
                "", "test@test.com",
            )
            secret_store.destroy_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "1",
                "test@test.com",
            )

            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret["status"] == "empty"
            assert secret["active_version_count"] == 0
            assert secret["masked_value"] is None
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_add_version_revives_empty(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-rev"
        env_name = "dev"
        secret_id = f"{test_prefix}-revive"

        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "first-value-123456",
                "", "test@test.com",
            )
            secret_store.destroy_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "1",
                "test@test.com",
            )

            # Add new version to empty secret
            secret_store.add_version(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "revived-value-123456",
                "test@test.com",
            )

            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret["status"] == "active"
            assert secret["active_version_count"] == 1
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_delete_secret_marks_destroyed(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-del"
        env_name = "dev"
        secret_id = f"{test_prefix}-delete"

        secret_store.create_secret(
            tenant_id, project_ref_id, env_name,
            "pl4m-host-dev", secret_id, "delete-me-123456",
            "", "test@test.com",
        )
        result = secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
        assert result["status"] == "destroyed"

        secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
        assert secret["status"] == "destroyed"
        assert secret["active_version_count"] == 0

    def test_short_secret_masked_as_none(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-shrt"
        env_name = "dev"
        secret_id = f"{test_prefix}-short"

        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, env_name,
                "pl4m-host-dev", secret_id, "abc",
                "", "test@test.com",
            )
            secret = secret_store.get_secret(tenant_id, project_ref_id, env_name, secret_id)
            assert secret["masked_value"] is None  # under 6 chars
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", secret_id)
            except Exception:
                pass

    def test_list_secrets(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-lst"
        env_name = "dev"
        sid1 = f"{test_prefix}-list-a"
        sid2 = f"{test_prefix}-list-b"

        try:
            secret_store.create_secret(tenant_id, project_ref_id, env_name,
                                       "pl4m-host-dev", sid1, "value-aaa-123456", "", "test@test.com")
            secret_store.create_secret(tenant_id, project_ref_id, env_name,
                                       "pl4m-host-dev", sid2, "value-bbb-123456", "", "test@test.com")
            secrets = secret_store.list_secrets(tenant_id, project_ref_id, env_name)
            ids = [s["secret_id"] for s in secrets]
            assert sid1 in ids
            assert sid2 in ids
        finally:
            for sid in [sid1, sid2]:
                try:
                    secret_store.delete_secret(tenant_id, project_ref_id, env_name, "pl4m-host-dev", sid)
                except Exception:
                    pass
```

- [ ] **Step 2: Run integration tests**

Run: `set -a && source .env.test && set +a && python -m pytest packages/tests/integration/test_store_secrets.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_store_secrets.py
git commit -m "test: add Firestore secrets store integration tests"
```

---

### Task 5: Integration tests — API endpoints

**Files:**
- Create: `packages/tests/integration/test_api_secrets.py`

- [ ] **Step 1: Write API integration tests**

```python
"""Integration tests for env-scoped secret API endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestSecretAPI:
    def test_create_and_list(self, api_client, test_prefix):
        env = "dev"
        # Need a project first — use a project_ref_id that maps to a real project
        # For API tests, the dev user's tenant has access
        secret_id = f"{test_prefix}-api-sec"
        prefix = f"/api/projects/test-proj/envs/{env}/secrets"

        # Create
        resp = api_client.post(prefix, json={
            "secret_id": secret_id,
            "value": "api-test-value-123456",
            "description": "API test secret",
        })
        # May fail if test-proj doesn't exist — that's expected in some test configs
        if resp.status_code == 404:
            pytest.skip("Test project not found — need project setup for API tests")

        assert resp.status_code == 200
        data = resp.json()
        assert data["secret_id"] == secret_id

        try:
            # List
            list_resp = api_client.get(prefix)
            assert list_resp.status_code == 200
            secrets = list_resp.json()["secrets"]
            ids = [s["secret_id"] for s in secrets]
            assert secret_id in ids

            # Get with versions
            get_resp = api_client.get(f"{prefix}/{secret_id}")
            assert get_resp.status_code == 200
            detail = get_resp.json()
            assert detail["secret_id"] == secret_id
            assert "versions" in detail

            # Add version
            ver_resp = api_client.put(f"{prefix}/{secret_id}", json={"value": "updated-value-654321"})
            assert ver_resp.status_code == 200

            # List versions
            ver_list_resp = api_client.get(f"{prefix}/{secret_id}/versions")
            assert ver_list_resp.status_code == 200
            versions = ver_list_resp.json()["versions"]
            assert len(versions) >= 2

            # Destroy version
            del_ver_resp = api_client.delete(f"{prefix}/{secret_id}/versions/1")
            assert del_ver_resp.status_code == 200
            assert del_ver_resp.json()["status"] == "destroyed"

            # Delete secret
            del_resp = api_client.delete(f"{prefix}/{secret_id}")
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "destroyed"
        except Exception:
            # Cleanup
            api_client.delete(f"{prefix}/{secret_id}")
            raise

    def test_create_missing_fields(self, api_client):
        prefix = "/api/projects/test-proj/envs/dev/secrets"
        resp = api_client.post(prefix, json={"value": "something"})
        if resp.status_code == 404:
            pytest.skip("Test project not found")
        assert resp.status_code == 422

    def test_add_version_missing_value(self, api_client):
        prefix = "/api/projects/test-proj/envs/dev/secrets/nonexistent"
        resp = api_client.put(prefix, json={})
        if resp.status_code == 404:
            pytest.skip("Test project not found")
        assert resp.status_code == 422
```

- [ ] **Step 2: Run API integration tests**

Run: `set -a && source .env.test && set +a && python -m pytest packages/tests/integration/test_api_secrets.py -v -m integration`
Expected: Tests PASS (or skip if test project isn't set up for API-level access).

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_secrets.py
git commit -m "test: add env-scoped secret API integration tests"
```

---

### Task 6: Run full test suite

**Files:** None (verification only)

- [ ] **Step 1: Run core unit tests**

Run: `python -m pytest packages/tests/ -v --tb=short -m "not integration"`
Expected: All core tests PASS (including new masking tests).

- [ ] **Step 2: Run integration tests**

Run: `set -a && source .env.test && set +a && python -m pytest packages/tests/ -v --tb=short -m integration`
Expected: All integration tests PASS (existing + new secrets tests).

- [ ] **Step 3: Run everything**

Run: `set -a && source .env.test && set +a && python -m pytest packages/tests/ -v --tb=short`
Expected: Full green.
