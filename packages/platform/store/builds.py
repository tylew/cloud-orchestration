"""Build record CRUD for Firestore."""

from datetime import datetime, timezone
from google.cloud import firestore
from packages.platform.store.client import get_client, _tenants_ref


def create_build_record(tenant_id: str, project_id: str, env_name: str, node_name: str, config: dict) -> str:
    """Create a build record for a compute node. Returns build_record_id."""
    client = get_client()
    now = datetime.now(timezone.utc)
    doc_ref = _tenants_ref(tenant_id).collection("builds").document()
    doc_ref.set({
        "project_id": project_id,
        "env_name": env_name,
        "node_name": node_name,
        "status": "queued",
        "build_id": None,
        "image_uri": config.get("image_uri", ""),
        "source_hash": config.get("source_hash", ""),
        "log_url": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    })
    return doc_ref.id


def update_build_record(tenant_id: str, build_record_id: str, **kwargs):
    """Update build record fields (status, build_id, log_url, image_uri, error)."""
    client = get_client()
    now = datetime.now(timezone.utc)
    updates = {k: v for k, v in kwargs.items() if v is not None}
    updates["updated_at"] = now
    _tenants_ref(tenant_id).collection("builds").document(build_record_id).update(updates)


def get_build_record(tenant_id: str, build_record_id: str) -> dict | None:
    """Get a single build record."""
    doc = _tenants_ref(tenant_id).collection("builds").document(build_record_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def get_latest_build_for_node(tenant_id: str, project_id: str, env_name: str, node_name: str) -> dict | None:
    """Get the most recent build record for a specific node."""
    client = get_client()
    query = (_tenants_ref(tenant_id).collection("builds")
             .where("project_id", "==", project_id)
             .where("env_name", "==", env_name)
             .where("node_name", "==", node_name)
             .order_by("created_at", direction=firestore.Query.DESCENDING)
             .limit(1))
    docs = list(query.stream())
    if not docs:
        return None
    data = docs[0].to_dict()
    data["id"] = docs[0].id
    return data


def list_build_records(tenant_id: str, project_id: str, env_name: str) -> list[dict]:
    """List latest build record per node for an environment."""
    client = get_client()
    query = (_tenants_ref(tenant_id).collection("builds")
             .where("project_id", "==", project_id)
             .where("env_name", "==", env_name)
             .order_by("created_at", direction=firestore.Query.DESCENDING))
    docs = list(query.stream())
    # Deduplicate: keep only the latest per node_name
    seen = set()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if data["node_name"] not in seen:
            seen.add(data["node_name"])
            results.append(data)
    return results
