"""Project lifecycle CRUD for Firestore."""

from datetime import datetime, timezone
from google.cloud import firestore
from packages.platform.store.client import get_client, _tenants_ref, _project_ref, _batch_commit


# ── Environment Helpers ───────────────────────────────────────

def get_env_entry(environments: list[dict], env_name: str) -> dict | None:
    """Find an environment entry by name from the environments list."""
    for env in environments:
        if isinstance(env, dict) and env.get("name") == env_name:
            return env
    return None


# ── Activity Log ──────────────────────────────────────────────

def add_activity(tenant_id: str, project_ref_id: str, action: str, env: str,
                 user_email: str, user_display_name: str, details: dict | None = None):
    ref = _project_ref(tenant_id, project_ref_id).collection("activity")
    now = datetime.now(timezone.utc)
    doc_data = {
        "action": action,
        "env": env,
        "user_email": user_email,
        "user_display_name": user_display_name,
        "timestamp": now,
    }
    if details:
        doc_data["details"] = details
    ref.add(doc_data)


def list_activity(tenant_id: str, project_ref_id: str, limit: int = 50) -> list[dict]:
    ref = _project_ref(tenant_id, project_ref_id).collection("activity")
    query = ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    results = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        # Convert timestamp to ISO string for JSON
        if "timestamp" in d and hasattr(d["timestamp"], "isoformat"):
            d["timestamp"] = d["timestamp"].isoformat()
        results.append(d)
    return results


# ── Projects ─────────────────────────────────────────────────

def get_project(tenant_id: str, project_ref_id: str) -> dict | None:
    doc = _project_ref(tenant_id, project_ref_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def find_project_for_user(user_uid: str, project_ref_id: str) -> tuple[dict | None, str | None]:
    """Find a project accessible to this user. Returns (project_doc, owner_uid) or (None, None).

    Checks:
    1. User's own projects: tenants/{user_uid}/projects/{project_ref_id}
    2. Shared projects index: shared_projects/{user_uid}/projects/{project_ref_id}
       -> get owner_uid -> tenants/{owner_uid}/projects/{project_ref_id}
    """
    # Check user's own projects first (most common case)
    project = get_project(user_uid, project_ref_id)
    if project:
        return project, user_uid

    # Check shared_projects index for this specific project
    client = get_client()
    shared_ref = (client.collection("shared_projects")
                  .document(user_uid)
                  .collection("projects")
                  .document(project_ref_id))
    shared_snap = shared_ref.get()
    if shared_snap.exists:
        shared_data = shared_snap.to_dict()
        owner_uid = shared_data.get("owner_uid")
        if owner_uid:
            project = get_project(owner_uid, project_ref_id)
            if project:
                return project, owner_uid

    return None, None


def update_project_settings(tenant_id: str, project_ref_id: str, updates: dict) -> dict:
    """Update project settings. Validates immutable fields and max 3 envs."""
    doc_ref = _project_ref(tenant_id, project_ref_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    current = doc.to_dict()

    # Validate max 3 envs
    if "environments" in updates:
        envs = updates["environments"]
        if len(envs) > 3:
            raise ValueError("Maximum 3 environments allowed")
        # Cannot remove deployed envs
        current_envs = current.get("environments", [])
        for ce in current_envs:
            if isinstance(ce, dict) and ce.get("deployed"):
                # Check if this env still exists in the update
                if not any(e.get("id") == ce["id"] for e in envs if isinstance(e, dict)):
                    raise ValueError(f"Cannot remove deployed environment: {ce.get('name')}")

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now
    doc_ref.update(updates)

    updated = doc_ref.get().to_dict()
    updated["id"] = doc_ref.id
    return updated


def mark_env_deployed(tenant_id: str, project_ref_id: str, env_name: str) -> dict:
    """Mark an environment as deployed."""
    doc_ref = _project_ref(tenant_id, project_ref_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    data = doc.to_dict()
    envs = data.get("environments", [])
    now = datetime.now(timezone.utc)

    for env in envs:
        if isinstance(env, dict) and env.get("name") == env_name:
            env["deployed"] = True
            env["deployed_at"] = now
            break

    doc_ref.update({"environments": envs, "updated_at": now})
    return {"env": env_name, "deployed": True, "deployed_at": now.isoformat()}


def save_project(tenant_id: str, project_data: dict) -> dict:
    ref = _tenants_ref(tenant_id).collection("projects")
    now = datetime.now(timezone.utc)
    # Normalize environments list (replaces old single 'environment' field)
    if "environments" not in project_data or not project_data["environments"]:
        project_data["environments"] = ["prod"]
    project_data.pop("environment", None)
    project_data["created_at"] = now
    project_data["owner_uid"] = tenant_id
    project_data.setdefault("collaborators", {})
    _, doc_ref = ref.add(project_data)
    return {"id": doc_ref.id, **project_data, "created_at": now.isoformat()}


def list_projects(tenant_id: str) -> list[dict]:
    """List owned projects + projects shared with this user."""
    from packages.platform.store.collaborators import list_shared_projects

    ref = _tenants_ref(tenant_id).collection("projects")
    results = []
    for doc in ref.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        d["role"] = "owner"
        results.append(d)

    # Merge shared projects
    shared = list_shared_projects(tenant_id)
    for sp in shared:
        owner_uid = sp.get("owner_uid")
        project_ref_id = sp.get("id")
        if not owner_uid or not project_ref_id:
            continue
        # Skip if already in owned list
        if any(r["id"] == project_ref_id for r in results):
            continue
        project = get_project(owner_uid, project_ref_id)
        if project:
            project["role"] = sp.get("role", "viewer")
            project["owner_uid"] = owner_uid
            results.append(project)

    return results


def delete_project(tenant_id: str, project_ref_id: str) -> bool:
    """Delete project and ALL subcollections (HARD-05)."""
    doc_ref = _tenants_ref(tenant_id).collection("projects").document(project_ref_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False

    # Clean up blueprint and deploy data first (reuse existing helper)
    reset_project_data(tenant_id, project_ref_id, blueprints=True, deploy_status=True)

    # Delete remaining subcollections: activity, node_deploy_status, builds
    # NOTE: _batch_commit already handles >500 docs by chunking into 500-op batches
    # (see client.py lines 26-31), so no additional pagination needed here.
    client = get_client()
    project_ref = _project_ref(tenant_id, project_ref_id)
    for coll_name in ("activity", "node_deploy_status", "builds"):
        ops = []
        for doc in project_ref.collection(coll_name).list_documents():
            ops.append(lambda batch, r=doc: batch.delete(r))
        if ops:
            _batch_commit(client, ops)

    # Finally delete the project document itself
    doc_ref.delete()
    return True


# ── Project Reset ────────────────────────────────────────────

def reset_project_data(
    tenant_id: str,
    project_ref_id: str,
    blueprints: bool = True,
    deploy_status: bool = True,
) -> dict:
    """Selectively delete project data. Returns counts of deleted items per category."""
    client = get_client()
    project_ref = _project_ref(tenant_id, project_ref_id)
    blueprints_deleted = 0
    nodes_deleted = 0
    deploys_deleted = 0

    if blueprints:
        # Delete all env blueprint docs and their node subcollections
        for env_doc in project_ref.collection("blueprints").list_documents():
            # Delete nodes subcollection first
            node_ops = []
            for node_doc in env_doc.collection("nodes").list_documents():
                node_ops.append(lambda b, ref=node_doc: b.delete(ref))
                nodes_deleted += 1
            _batch_commit(client, node_ops)
            # Delete the env blueprint doc itself
            env_doc.delete()
            blueprints_deleted += 1

    if deploy_status:
        # Delete all deploy tracking records for this tenant
        deploy_ops = []
        for deploy_doc in _tenants_ref(tenant_id).collection("deploys").stream():
            deploy_data = deploy_doc.to_dict()
            if deploy_data.get("project_id") == project_ref_id:
                deploy_ops.append(lambda b, ref=deploy_doc.reference: b.delete(ref))
                deploys_deleted += 1
        _batch_commit(client, deploy_ops)

    return {
        "blueprints_deleted": blueprints_deleted,
        "nodes_deleted": nodes_deleted,
        "deploys_deleted": deploys_deleted,
    }
