"""GCP Secret Manager CRUD service.

Secret values are stored ONLY in GCP Secret Manager (never Firestore).
Uses google-cloud-secret-manager SDK.
"""
import logging
from google.cloud import secretmanager

log = logging.getLogger(__name__)


def _get_sm_client():
    return secretmanager.SecretManagerServiceClient()


def create_secret_with_value(project_id: str, secret_id: str, value: str) -> dict:
    """Create a new secret and its first version. Returns {"secret_name": ..., "version": ...}"""
    client = _get_sm_client()
    parent = f"projects/{project_id}"
    secret = client.create_secret(
        request={"parent": parent, "secret_id": secret_id,
                 "secret": {"replication": {"automatic": {}}}}
    )
    version = client.add_secret_version(
        request={"parent": secret.name,
                 "payload": {"data": value.encode("UTF-8")}}
    )
    return {"secret_name": secret.name, "version": version.name}


def add_secret_version(project_id: str, secret_id: str, value: str) -> str:
    """Add a new version to an existing secret. Returns version name."""
    client = _get_sm_client()
    parent = f"projects/{project_id}/secrets/{secret_id}"
    version = client.add_secret_version(
        request={"parent": parent,
                 "payload": {"data": value.encode("UTF-8")}}
    )
    return version.name


def get_secret_value(project_id: str, secret_id: str, version: str = "latest") -> str:
    """Read the value of a secret version."""
    client = _get_sm_client()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def list_secrets(project_id: str) -> list[dict]:
    """List all secrets in a project. Returns [{"name": ..., "secret_id": ..., "create_time": ...}]"""
    client = _get_sm_client()
    parent = f"projects/{project_id}"
    secrets = client.list_secrets(request={"parent": parent})
    results = []
    for s in secrets:
        sid = s.name.split("/")[-1]
        results.append({"name": s.name, "secret_id": sid, "create_time": s.create_time.isoformat() if s.create_time else None})
    return results


def delete_secret(project_id: str, secret_id: str) -> None:
    """Delete a secret and all its versions."""
    client = _get_sm_client()
    name = f"projects/{project_id}/secrets/{secret_id}"
    client.delete_secret(request={"name": name})


def mask_secret_value(value: str) -> str:
    """Partial masking per D-12: sk-abc123xyz789 => sk-a...789"""
    if len(value) < 6:
        return "******"
    visible_start = min(4, len(value) * 15 // 100)
    visible_end = min(3, len(value) * 10 // 100)
    if visible_start < 1:
        visible_start = 1
    if visible_end < 1:
        visible_end = 1
    return f"{value[:visible_start]}...{value[-visible_end:]}"


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
