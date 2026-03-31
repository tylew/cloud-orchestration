"""Provision record CRUD for Firestore."""

from datetime import datetime, timezone
from packages.platform.store.client import get_client, _tenants_ref


def create_provision_record(tenant_id: str, project_id: str, config: dict) -> str:
    ref = _tenants_ref(tenant_id).collection("provisions")
    now = datetime.now(timezone.utc)
    doc_data = {
        "project_id": project_id,
        "config": config,
        "status": "pending",
        "steps": [],
        "created_at": now,
        "updated_at": now,
    }
    _, doc_ref = ref.add(doc_data)
    return doc_ref.id


def update_provision_status(tenant_id: str, provision_id: str, status: str,
                            step_result: dict | None = None, error: str | None = None):
    ref = _tenants_ref(tenant_id).collection("provisions").document(provision_id)
    now = datetime.now(timezone.utc)
    updates: dict = {"status": status, "updated_at": now}
    if error:
        updates["error"] = error
    ref.update(updates)
    if step_result:
        from google.cloud.firestore_v1 import transforms
        ref.update({"steps": transforms.ArrayUnion([{**step_result, "timestamp": now}])})


def get_provision_status(tenant_id: str, provision_id: str) -> dict | None:
    doc = _tenants_ref(tenant_id).collection("provisions").document(provision_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    # Convert timestamps
    for key in ("created_at", "updated_at"):
        if key in data and hasattr(data[key], "isoformat"):
            data[key] = data[key].isoformat()
    for step in data.get("steps", []):
        if "timestamp" in step and hasattr(step["timestamp"], "isoformat"):
            step["timestamp"] = step["timestamp"].isoformat()
    return data
