"""GCS-backed code file storage for compute node source code."""

import os
import logging
from google.cloud import storage

log = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("CB_SOURCE_BUCKET", "")


def _get_prefix(project_id: str, env_name: str, node_name: str) -> str:
    """Build GCS prefix: {project_id}/source/{env_name}/{node_name}/"""
    return f"{project_id}/source/{env_name}/{node_name}/"


def _get_client():
    """Get GCS client. Returns None in test/dev environments without GCS."""
    try:
        return storage.Client()
    except Exception:
        log.warning("GCS client unavailable -- code storage operations will fail")
        return None


def list_files(project_id: str, env_name: str, node_name: str) -> list[str]:
    """List all files for a compute node."""
    client = _get_client()
    if not client or not BUCKET_NAME:
        return []
    prefix = _get_prefix(project_id, env_name, node_name)
    bucket = client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name[len(prefix):] for blob in blobs if blob.name != prefix]


def read_file(project_id: str, env_name: str, node_name: str, file_path: str) -> str | None:
    """Read a single file's content. Returns None if not found."""
    client = _get_client()
    if not client or not BUCKET_NAME:
        return None
    prefix = _get_prefix(project_id, env_name, node_name)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(prefix + file_path)
    if not blob.exists():
        return None
    return blob.download_as_text()


def write_file(project_id: str, env_name: str, node_name: str, file_path: str, content: str) -> bool:
    """Write content to a file. Creates or overwrites."""
    client = _get_client()
    if not client or not BUCKET_NAME:
        return False
    prefix = _get_prefix(project_id, env_name, node_name)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(prefix + file_path)
    blob.upload_from_string(content, content_type="text/plain")
    return True


def delete_file(project_id: str, env_name: str, node_name: str, file_path: str) -> bool:
    """Delete a file. Returns True if deleted, False if not found."""
    client = _get_client()
    if not client or not BUCKET_NAME:
        return False
    prefix = _get_prefix(project_id, env_name, node_name)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(prefix + file_path)
    if not blob.exists():
        return False
    blob.delete()
    return True
