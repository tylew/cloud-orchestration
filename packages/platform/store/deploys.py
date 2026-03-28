"""Deploy record CRUD for Firestore."""

from datetime import datetime, timezone
from packages.platform.store.client import get_client, _tenants_ref, _project_ref


def create_deploy_record(tenant_id: str, project_id: str, env_name: str, config: dict) -> str:
    ref = _tenants_ref(tenant_id).collection("deploys")
    now = datetime.now(timezone.utc)
    doc_data = {
        "project_id": project_id,
        "env_name": env_name,
        "config": config,
        "status": "pending",
        "steps": [],
        "plan_output": None,
        "apply_output": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    _, doc_ref = ref.add(doc_data)
    return doc_ref.id


def update_deploy_status(tenant_id: str, deploy_id: str, status: str,
                         step_result: dict | None = None, error: str | None = None,
                         plan_output: str | None = None, apply_output: str | None = None,
                         build_id: str | None = None, log_url: str | None = None,
                         terraform_outputs: dict | None = None):
    ref = _tenants_ref(tenant_id).collection("deploys").document(deploy_id)
    now = datetime.now(timezone.utc)
    updates: dict = {"status": status, "updated_at": now}
    if error:
        updates["error"] = error
    if plan_output is not None:
        updates["plan_output"] = plan_output
    if apply_output is not None:
        updates["apply_output"] = apply_output
    if build_id is not None:
        updates["build_id"] = build_id
    if log_url is not None:
        updates["log_url"] = log_url
    if terraform_outputs is not None:
        updates["terraform_outputs"] = terraform_outputs
    ref.update(updates)
    if step_result:
        from google.cloud.firestore_v1 import transforms
        ref.update({"steps": transforms.ArrayUnion([{**step_result, "timestamp": now}])})


def get_deploy_status(tenant_id: str, deploy_id: str) -> dict | None:
    doc = _tenants_ref(tenant_id).collection("deploys").document(deploy_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    for key in ("created_at", "updated_at"):
        if key in data and hasattr(data[key], "isoformat"):
            data[key] = data[key].isoformat()
    for step in data.get("steps", []):
        if "timestamp" in step and hasattr(step["timestamp"], "isoformat"):
            step["timestamp"] = step["timestamp"].isoformat()
    return data


def list_deploys(tenant_id: str, project_ref_id: str, limit: int = 50) -> list[dict]:
    """List deploy records for a project, ordered by creation time descending."""
    from google.cloud import firestore
    ref = _tenants_ref(tenant_id).collection("deploys")
    q = (ref.where("project_id", "==", project_ref_id)
         .order_by("created_at", direction=firestore.Query.DESCENDING)
         .limit(limit))
    results = []
    for doc in q.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        for key in ("created_at", "updated_at"):
            if key in data and hasattr(data[key], "isoformat"):
                data[key] = data[key].isoformat()
        for step in data.get("steps", []):
            if "timestamp" in step and hasattr(step["timestamp"], "isoformat"):
                step["timestamp"] = step["timestamp"].isoformat()
        results.append(data)
    return results


def update_node_deploy_status(tenant_id: str, deploy_id: str, node_name: str, status: str):
    """Update per-node deploy status on a deploy record (per D-09)."""
    now = datetime.now(timezone.utc)
    ref = _tenants_ref(tenant_id).collection("deploys").document(deploy_id)
    ref.update({
        f"node_statuses.{node_name}": {"status": status, "updated_at": now},
        "updated_at": now,
    })


def save_deploy_snapshot(tenant_id: str, deploy_id: str, node_name: str, snapshot_data: dict):
    """Save a deploy snapshot for a node as a subcollection document (per D-11)."""
    ref = (_tenants_ref(tenant_id).collection("deploys").document(deploy_id)
           .collection("snapshots").document(node_name))
    ref.set(snapshot_data)


def get_node_deploy_status_doc(tenant_id: str, project_ref_id: str, env_name: str) -> dict:
    """Get the node deploy status document for an environment."""
    ref = _project_ref(tenant_id, project_ref_id).collection("node_deploy_status").document(env_name)
    doc = ref.get()
    if not doc.exists:
        return {"nodes": {}}
    return doc.to_dict() or {"nodes": {}}


def update_node_deploy_version(tenant_id: str, project_ref_id: str, env_name: str,
                               node_name: str, version_data: dict):
    """Update per-node deploy version in the node_deploy_status document (merge)."""
    ref = _project_ref(tenant_id, project_ref_id).collection("node_deploy_status").document(env_name)
    ref.set({f"nodes.{node_name}": version_data}, merge=True)


def save_env_outputs(tenant_id: str, project_ref_id: str, env_name: str,
                     outputs: dict, deploy_id: str):
    """Write latest TF outputs to env_outputs/{env} for fast agent lookup (D-04)."""
    ref = _project_ref(tenant_id, project_ref_id).collection("env_outputs").document(env_name)
    ref.set({
        "outputs": outputs.get("outputs", {}),
        "by_node": outputs.get("by_node", {}),
        "deploy_id": deploy_id,
        "captured_at": datetime.now(timezone.utc),
    })


def get_env_outputs(tenant_id: str, project_ref_id: str, env_name: str) -> dict | None:
    """Read latest TF outputs for an environment (D-05)."""
    ref = _project_ref(tenant_id, project_ref_id).collection("env_outputs").document(env_name)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    if "captured_at" in data and hasattr(data["captured_at"], "isoformat"):
        data["captured_at"] = data["captured_at"].isoformat()
    return data
