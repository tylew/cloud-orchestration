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
    """Create a new secret in Firestore + GCP Secret Manager."""
    now = datetime.now(timezone.utc).isoformat()
    doc_ref = _secret_ref(tenant_id, project_ref_id, env_name, secret_id)

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

    try:
        result = sm.create_secret_with_value(project_id, secret_id, value)
    except Exception as e:
        doc_ref.update({"status": "failed"})
        raise

    masked = sm.safe_mask(value)
    version_num = result["version"].split("/")[-1]
    _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version_num).set({
        "version": version_num,
        "status": "active",
        "created_at": now,
        "created_by": user_email,
        "destroyed_at": None,
        "destroyed_by": None,
        "masked_value": masked,
    })

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
    version_name = sm.add_secret_version(project_id, secret_id, value)

    now = datetime.now(timezone.utc).isoformat()
    masked = sm.safe_mask(value)
    version_num = version_name.split("/")[-1]

    _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version_num).set({
        "version": version_num,
        "status": "active",
        "created_at": now,
        "created_by": user_email,
        "destroyed_at": None,
        "destroyed_by": None,
        "masked_value": masked,
    })

    doc_ref = _secret_ref(tenant_id, project_ref_id, env_name, secret_id)
    doc = doc_ref.get()
    current = doc.to_dict() if doc.exists else {}
    count = current.get("active_version_count", 0) + 1
    updates = {
        "latest_version": version_num,
        "active_version_count": count,
        "masked_value": masked,
    }
    if current.get("status") == "empty":
        updates["status"] = "active"
    doc_ref.update(updates)

    return {"secret_id": secret_id, "version": version_num}


def destroy_version(tenant_id: str, project_ref_id: str, env_name: str,
                    project_id: str, secret_id: str, version: str,
                    user_email: str) -> dict:
    """Destroy a specific version (soft delete in Firestore, real destroy in GCP SM)."""
    sm.destroy_secret_version(project_id, secret_id, version)

    now = datetime.now(timezone.utc).isoformat()

    ver_ref = _versions_ref(tenant_id, project_ref_id, env_name, secret_id).document(version)
    ver_ref.update({
        "status": "destroyed",
        "destroyed_at": now,
        "destroyed_by": user_email,
    })

    _recalculate_parent(tenant_id, project_ref_id, env_name, secret_id)

    return {"secret_id": secret_id, "version": version, "status": "destroyed"}


def delete_secret(tenant_id: str, project_ref_id: str, env_name: str,
                  project_id: str, secret_id: str) -> dict:
    """Delete entire secret from GCP SM, mark as destroyed in Firestore."""
    sm.delete_secret(project_id, secret_id)

    now = datetime.now(timezone.utc).isoformat()

    versions_coll = _versions_ref(tenant_id, project_ref_id, env_name, secret_id)
    for doc in versions_coll.stream():
        doc.reference.update({"status": "destroyed", "destroyed_at": now})

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
    results.sort(key=lambda v: int(v.get("version", "0")), reverse=True)
    return results


def _recalculate_parent(tenant_id: str, project_ref_id: str, env_name: str,
                        secret_id: str) -> None:
    """Recalculate parent doc fields after a version status change."""
    versions = list_versions(tenant_id, project_ref_id, env_name, secret_id)
    active = [v for v in versions if v.get("status") == "active"]
    count = len(active)

    masked = active[0].get("masked_value") if active else None

    updates: dict = {
        "active_version_count": count,
        "masked_value": masked,
    }
    if count == 0:
        updates["status"] = "empty"

    _secret_ref(tenant_id, project_ref_id, env_name, secret_id).update(updates)
