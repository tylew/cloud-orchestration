"""Blueprint, node, and validation CRUD for Firestore."""

import copy
from datetime import datetime, timezone
from packages.platform.store.client import get_client, _project_ref, _batch_commit

# Frontend-only fields that must not be persisted or returned by the store layer (HARD-03)
_FRONTEND_ONLY_FIELDS = frozenset({"position", "dimensions", "onCanvas"})

_COMPUTE_TYPES = frozenset({"cloud_run", "cloud_function", "cloud_run_job"})


def _strip_env_var_values(nodes: list[dict]) -> list[dict]:
    """Deep copy nodes, stripping env var values/secrets on compute nodes for promotion."""
    result = copy.deepcopy(nodes)
    for node in result:
        if node.get("type") not in _COMPUTE_TYPES:
            continue
        config = node.get("config", {})
        env_vars = config.get("env_vars", [])
        for entry in env_vars:
            if entry.get("type") == "value":
                entry["value"] = None
            elif entry.get("type") == "secret":
                entry["secret"] = None
                entry["version"] = "latest"
    return result


# ── Env-scoped Blueprints (sharded into subcollections) ──────

def save_env_blueprint(tenant_id: str, project_ref_id: str, env_name: str, envelope: dict) -> dict:
    """Save blueprint for a specific project environment, sharding nodes into subcollection.

    Returns dict with env, updated_at, node_count, and changes summary.
    """
    client = get_client()
    parent_ref = _project_ref(tenant_id, project_ref_id).collection("blueprints").document(env_name)
    nodes_coll = parent_ref.collection("nodes")
    now = datetime.now(timezone.utc)

    # Single flat nodes[] — no category split (D-04)
    all_nodes = envelope.get("nodes", [])
    node_docs = {}
    for n in all_nodes:
        slug = n.get("slug") or n.get("name")  # fallback to name for backward compat
        doc_data = {
            "slug": slug,
            "name": n["name"],
            "type": n["type"],
            "config": n.get("config", {}),
        }
        if n.get("depends_on"):
            doc_data["depends_on"] = n["depends_on"]
        # position, dimensions, onCanvas intentionally excluded (HARD-03)
        node_docs[slug] = doc_data

    # Fetch existing subcollection doc IDs + data for diff
    existing_docs = {}
    for doc in nodes_coll.list_documents():
        snap = doc.get()
        if snap.exists:
            existing_docs[doc.id] = snap.to_dict()

    existing_slugs = set(existing_docs.keys())
    new_slugs = set(node_docs.keys())
    added = sorted(new_slugs - existing_slugs)
    removed = sorted(existing_slugs - new_slugs)

    # Detect modifications (compare backend-relevant fields only)
    modified = []
    for name in sorted(new_slugs & existing_slugs):
        old = existing_docs[name]
        new = node_docs[name]
        if (old.get("config") != new.get("config") or
            old.get("depends_on") != new.get("depends_on")):
            modified.append(name)

    changes = {"added": added, "removed": removed, "modified": modified}
    is_noop = not added and not removed and not modified

    # Build parent doc (everything except nodes/resources arrays)
    parent_data = {
        "version": envelope.get("version", "1.0.0"),
        "schema_version": envelope.get("version", "1.0.0"),
        "updated_at": now,
        "node_count": len(node_docs),
    }
    if "global" in envelope:
        parent_data["global"] = envelope["global"]
    if "projectSettings" in envelope:
        parent_data["projectSettings"] = envelope["projectSettings"]
    if "metadata" in envelope:
        parent_data["metadata"] = envelope["metadata"]
    if "$schema" in envelope:
        parent_data["$schema"] = envelope["$schema"]

    # Batch operations
    ops = []
    ops.append(lambda batch: batch.set(parent_ref, parent_data))
    for slug, doc_data in node_docs.items():
        ref = nodes_coll.document(slug)
        ops.append(lambda batch, r=ref, d=doc_data: batch.set(r, d))
    for slug in removed:
        ref = nodes_coll.document(slug)
        ops.append(lambda batch, r=ref: batch.delete(r))

    _batch_commit(client, ops)

    return {
        "env": env_name,
        "updated_at": now.isoformat(),
        "node_count": len(node_docs),
        "changes": changes,
        "is_noop": is_noop,
    }


def get_env_blueprint(tenant_id: str, project_ref_id: str, env_name: str) -> dict | None:
    """Read blueprint for an environment, reassembling from subcollection."""
    parent_ref = _project_ref(tenant_id, project_ref_id).collection("blueprints").document(env_name)
    parent_snap = parent_ref.get()
    if not parent_snap.exists:
        return None

    parent_data = parent_snap.to_dict()

    # Stream nodes subcollection — unified nodes[] (D-04)
    nodes = []
    for doc in parent_ref.collection("nodes").stream():
        d = doc.to_dict()
        node = {
            "slug": d.get("slug", doc.id),
            "name": d["name"],
            "type": d["type"],
            "config": d.get("config", {}),
        }
        if d.get("depends_on"):
            node["depends_on"] = d["depends_on"]
        # position, dimensions, onCanvas excluded from API response (HARD-03)
        nodes.append(node)

    # Reassemble envelope — single nodes[] array (no resources[])
    envelope = {
        "$schema": parent_data.get("$schema", "GCP_NESTED_SUBGRAPH_V1"),
        "version": parent_data.get("version", "1.0.0"),
        "global": parent_data.get("global", {}),
        "projectSettings": parent_data.get("projectSettings", {}),
        "nodes": nodes,
        "metadata": parent_data.get("metadata", {}),
    }

    return {"env": env_name, "envelope": envelope}


def promote_blueprint(tenant_id: str, project_ref_id: str, source_env: str, target_env: str) -> dict:
    """Copy blueprint from source_env to target_env."""
    source = get_env_blueprint(tenant_id, project_ref_id, source_env)
    if not source:
        raise ValueError(f"No blueprint found for env '{source_env}'")

    envelope = source.get("envelope", {})

    # Strip env var values on compute nodes
    original_nodes = envelope.get("nodes", [])
    envelope["nodes"] = _strip_env_var_values(original_nodes)

    # Delete all existing target subcollection docs
    client = get_client()
    target_ref = _project_ref(tenant_id, project_ref_id).collection("blueprints").document(target_env)
    target_nodes_coll = target_ref.collection("nodes")
    delete_ops = []
    for doc in target_nodes_coll.list_documents():
        delete_ops.append(lambda batch, r=doc: batch.delete(r))
    if delete_ops:
        _batch_commit(client, delete_ops)

    nodes_deleted = len(delete_ops)

    # Write target via save
    result = save_env_blueprint(tenant_id, project_ref_id, target_env, envelope)
    now = datetime.now(timezone.utc)

    # Update target parent with promotion metadata
    target_ref.update({
        "promoted_from": source_env,
        "promoted_at": now,
    })

    return {
        "nodes_copied": result["node_count"],
        "nodes_deleted": nodes_deleted,
        "promoted_from": source_env,
        "promoted_at": now.isoformat(),
    }


# ── Individual Node CRUD ──────────────────────────────────────


def save_node(tenant_id: str, project_ref_id: str, env_name: str,
              slug: str, node_data: dict) -> dict:
    """Write a single node document keyed by slug."""
    ref = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("nodes").document(slug)
    # Strip frontend-only fields before persistence (HARD-03)
    cleaned = {k: v for k, v in node_data.items() if k not in _FRONTEND_ONLY_FIELDS}
    cleaned["updated_at"] = datetime.now(timezone.utc)
    ref.set(cleaned)
    return cleaned


def get_node(tenant_id: str, project_ref_id: str, env_name: str,
             slug: str) -> dict | None:
    """Get a single node document by slug."""
    ref = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("nodes").document(slug)
    snap = ref.get()
    return snap.to_dict() if snap.exists else None


def delete_node(tenant_id: str, project_ref_id: str, env_name: str,
                slug: str) -> list[str]:
    """Delete a node and cascade-delete children (by parentRef). Returns deleted slugs."""
    client = get_client()
    bp_ref = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name)
    nodes_coll = bp_ref.collection("nodes")

    # Find children with parentRef == slug
    children = nodes_coll.where("config.parentRef", "==", slug).stream()
    deleted_slugs = [slug]
    ops = []
    for child_snap in children:
        deleted_slugs.append(child_snap.id)
        ops.append(lambda batch, r=nodes_coll.document(child_snap.id): batch.delete(r))
    ops.append(lambda batch: batch.delete(nodes_coll.document(slug)))
    _batch_commit(client, ops)
    return deleted_slugs


def list_nodes(tenant_id: str, project_ref_id: str, env_name: str) -> list[dict]:
    """List all nodes for an environment."""
    nodes_coll = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("nodes")
    result = []
    for snap in nodes_coll.stream():
        d = snap.to_dict()
        # Exclude frontend-only fields from API response (HARD-03)
        result.append({k: v for k, v in d.items() if k not in _FRONTEND_ONLY_FIELDS})
    return result


# ── Validation Doc Persistence (D-03) ────────────────────────


def save_validation_doc(tenant_id: str, project_ref_id: str, env_name: str,
                        validation_data: dict) -> None:
    """Persist validation results for a blueprint environment (D-03).

    Canonical Firestore path (used consistently across Plans 01, 03, 05):
      tenants/{tid}/projects/{pid}/blueprints/{env}/validation/current

    This is a subcollection 'validation' under the blueprint env document,
    with a single document 'current' holding the latest validation state.
    Frontend subscribes to this path for real-time validation updates.
    """
    ref = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("validation").document("current")
    ref.set(validation_data)


def get_validation_doc(tenant_id: str, project_ref_id: str, env_name: str) -> dict | None:
    """Get persisted validation results.

    Reads from: tenants/{tid}/projects/{pid}/blueprints/{env}/validation/current
    """
    ref = _project_ref(tenant_id, project_ref_id) \
        .collection("blueprints").document(env_name) \
        .collection("validation").document("current")
    snap = ref.get()
    return snap.to_dict() if snap.exists else None
