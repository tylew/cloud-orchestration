"""Collaborator management for Firestore."""

from datetime import datetime, timezone
from packages.platform.store.client import get_client, _tenants_ref, _project_ref


VALID_ROLES = {"viewer", "editor", "admin"}


def add_collaborator(tenant_id: str, project_ref_id: str, email: str,
                     role: str = "editor", collaborator_uid: str | None = None) -> dict:
    """Invite a collaborator by email with a role. Optionally resolve UID now."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    doc_ref = _project_ref(tenant_id, project_ref_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise ValueError("Project not found")

    now = datetime.now(timezone.utc)

    # Resolve UID from email if not provided
    uid = collaborator_uid
    if not uid:
        from packages.platform.store.tenants import find_tenant_by_email
        tenant = find_tenant_by_email(email)
        uid = tenant["id"] if tenant else None

    if not uid:
        # Store as pending invitation keyed by email hash
        uid = f"pending-{email}"

    collab_data = {"email": email, "role": role, "added_at": now}
    doc_ref.update({f"collaborators.{uid}": collab_data})

    # Create shared_projects index entry so collaborator can discover this project
    if uid and not uid.startswith("pending-"):
        project_data = doc.to_dict()
        _create_shared_project_index(uid, project_ref_id, {
            "owner_uid": tenant_id,
            "role": role,
            "project_id": project_data.get("project_id", ""),
            "display_name": project_data.get("display_name", ""),
        })

    return {"uid": uid, "email": email, "role": role, "added_at": now.isoformat()}


def update_collaborator_role(tenant_id: str, project_ref_id: str,
                             collaborator_uid: str, role: str) -> dict:
    """Change a collaborator's role."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    doc_ref = _project_ref(tenant_id, project_ref_id)
    doc_ref.update({f"collaborators.{collaborator_uid}.role": role})

    # Update shared_projects index
    _update_shared_project_role(collaborator_uid, project_ref_id, role)

    return {"uid": collaborator_uid, "role": role}


def list_collaborators(tenant_id: str, project_ref_id: str) -> list[dict]:
    doc = _project_ref(tenant_id, project_ref_id).get()
    if not doc.exists:
        return []
    data = doc.to_dict()
    collabs_map = data.get("collaborators", {})
    if not isinstance(collabs_map, dict):
        # Legacy array format no longer supported -- treat as empty (HARD-07)
        return []

    result = []
    for uid, collab in collabs_map.items():
        entry = {"uid": uid, **collab}
        if "added_at" in entry and hasattr(entry["added_at"], "isoformat"):
            entry["added_at"] = entry["added_at"].isoformat()
        result.append(entry)
    return result


def remove_collaborator(tenant_id: str, project_ref_id: str,
                        collaborator_uid: str) -> bool:
    doc_ref = _project_ref(tenant_id, project_ref_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    data = doc.to_dict()
    collabs = data.get("collaborators", {})
    if isinstance(collabs, dict) and collaborator_uid in collabs:
        from google.cloud.firestore_v1 import transforms
        doc_ref.update({f"collaborators.{collaborator_uid}": transforms.DELETE_FIELD})
        # Remove shared_projects index
        _delete_shared_project_index(collaborator_uid, project_ref_id)
        return True
    return False


def get_collaborator_role(tenant_id: str, project_ref_id: str, uid: str) -> str | None:
    """Get a user's role on a project. Returns None if not a collaborator."""
    doc = _project_ref(tenant_id, project_ref_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    collabs = data.get("collaborators", {})
    if isinstance(collabs, dict) and uid in collabs:
        return collabs[uid].get("role")
    return None


# ── Shared Projects Index ─────────────────────────────────────

def _create_shared_project_index(uid: str, project_ref_id: str, data: dict):
    """Create entry in shared_projects/{uid}/projects/{projectRefId}."""
    ref = get_client().collection("shared_projects").document(uid).collection("projects").document(project_ref_id)
    ref.set(data)


def _update_shared_project_role(uid: str, project_ref_id: str, role: str):
    ref = get_client().collection("shared_projects").document(uid).collection("projects").document(project_ref_id)
    try:
        ref.update({"role": role})
    except Exception:
        pass  # Index may not exist yet


def _delete_shared_project_index(uid: str, project_ref_id: str):
    ref = get_client().collection("shared_projects").document(uid).collection("projects").document(project_ref_id)
    try:
        ref.delete()
    except Exception:
        pass


def list_shared_projects(uid: str) -> list[dict]:
    """List projects shared with a user via the index."""
    ref = get_client().collection("shared_projects").document(uid).collection("projects")
    results = []
    for doc in ref.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        results.append(d)
    return results
