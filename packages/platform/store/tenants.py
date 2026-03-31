"""Tenant and quota management for Firestore."""

from datetime import datetime, timezone
from packages.platform.store.client import get_client, _tenants_ref


def ensure_tenant(tenant_id: str, email: str = "", display_name: str = ""):
    """Create tenant doc if it doesn't exist."""
    doc_ref = _tenants_ref(tenant_id)
    doc = doc_ref.get()
    if not doc.exists:
        doc_ref.set({
            "owner_email": email,
            "display_name": display_name,
            "created_at": datetime.now(timezone.utc),
            "plan": "free",
            "quota": 0,
            "used_quota": 0,
        })


def get_tenant(tenant_id: str) -> dict | None:
    doc = _tenants_ref(tenant_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def update_tenant(tenant_id: str, updates: dict):
    """Update fields on a tenant document."""
    updates["updated_at"] = datetime.now(timezone.utc)
    _tenants_ref(tenant_id).update(updates)


def set_quota(tenant_id: str, quota: int):
    _tenants_ref(tenant_id).update({"quota": quota})


def increment_used_quota(tenant_id: str, count: int = 1):
    from google.cloud.firestore_v1 import transforms
    _tenants_ref(tenant_id).update({"used_quota": transforms.Increment(count)})


def check_quota(tenant_id: str) -> tuple[int, int]:
    doc = _tenants_ref(tenant_id).get()
    if not doc.exists:
        return (0, 0)
    data = doc.to_dict()
    return (data.get("quota", 0), data.get("used_quota", 0))


def find_tenant_by_email(email: str) -> dict | None:
    docs = get_client().collection("tenants").where("owner_email", "==", email).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


def list_tenants() -> list[dict]:
    results = []
    for doc in get_client().collection("tenants").stream():
        d = doc.to_dict()
        d["id"] = doc.id
        results.append(d)
    return results
