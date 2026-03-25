"""Deploy orchestration with image URI injection, per-node status, snapshots, and modified flag."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from packages.platform.store.builds import list_build_records
from packages.platform.store.deploys import (
    get_node_deploy_status_doc,
    save_deploy_snapshot,
    update_node_deploy_version,
)

log = logging.getLogger(__name__)


def inject_build_image_uris(tenant_id: str, project_id: str, env_name: str, envelope: dict) -> dict:
    """Inject built image URIs from build records into envelope before TF generation.

    For each node with a successful build record containing an image_uri,
    sets node["config"]["image"] to the built image URI (per D-01/D-02/D-03).
    """
    build_records = list_build_records(tenant_id, project_id, env_name)
    build_map = {}
    for rec in build_records:
        if rec.get("status") == "success" and rec.get("image_uri"):
            build_map[rec["node_name"]] = rec

    for node in envelope.get("nodes", []):
        node_name = node.get("name", "")
        if node_name in build_map:
            if "config" not in node:
                node["config"] = {}
            node["config"]["image"] = build_map[node_name]["image_uri"]

    return envelope


def compute_config_hash(config: dict) -> str:
    """Deterministic hash of node config for change detection.

    Same pattern as compute_source_hash in cloud_build.py.
    """
    raw = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _find_build_for_node(build_records: list[dict], node_name: str) -> dict | None:
    """Find the latest successful build record for a node."""
    for rec in build_records:
        if rec.get("node_name") == node_name and rec.get("status") == "success":
            return rec
    return None


def create_deploy_snapshots(tenant_id: str, deploy_id: str, project_ref_id: str,
                            env_name: str, envelope: dict) -> None:
    """Create deploy snapshots for each node with version counter increment (per D-11/D-12).

    For each node:
    1. Read current version from node_deploy_status doc (default 0)
    2. Increment version
    3. Save snapshot with config, hashes, version
    4. Update node deploy version record
    """
    # Pre-fetch build records so compute nodes can get their source_hash
    project_id = envelope.get("global", {}).get("project_id", "")
    build_records = list_build_records(tenant_id, project_id, env_name) if project_id else []

    status_doc = get_node_deploy_status_doc(tenant_id, project_ref_id, env_name)
    nodes_map = status_doc.get("nodes", {})

    for node in envelope.get("nodes", []):
        node_name = node.get("name", "")
        node_type = node.get("type", "")
        config = node.get("config", {})

        # Read current version, increment (per D-12)
        current_version = 0
        if node_name in nodes_map:
            current_version = nodes_map[node_name].get("version", 0)
        new_version = current_version + 1

        config_hash = compute_config_hash(config)

        # Get source_hash from latest build record for compute types
        source_hash = None
        compute_types = {"cloud_run", "cloud_run_job", "cloud_function"}
        if node_type in compute_types:
            # Look up the latest successful build to get the source_hash
            build_rec = _find_build_for_node(build_records, node_name)
            if build_rec:
                source_hash = build_rec.get("source_hash")

        now = datetime.now(timezone.utc).isoformat()

        snapshot_data = {
            "node_name": node_name,
            "node_type": node_type,
            "version": new_version,
            "config_snapshot": config,
            "source_hash": source_hash,
            "config_hash": config_hash,
            "deployed_at": now,
            "deploy_id": deploy_id,
        }
        save_deploy_snapshot(tenant_id, deploy_id, node_name, snapshot_data)

        version_data = {
            "status": "deployed",
            "version": new_version,
            "deployed_at": now,
            "deploy_id": deploy_id,
            "config_hash": config_hash,
            "source_hash": source_hash,
            "modified": False,
        }
        update_node_deploy_version(tenant_id, project_ref_id, env_name, node_name, version_data)


def get_node_deploy_statuses(tenant_id: str, project_ref_id: str, env_name: str) -> dict:
    """Get per-node deploy statuses for an environment."""
    doc = get_node_deploy_status_doc(tenant_id, project_ref_id, env_name)
    return doc.get("nodes", {})


def compute_modified_flags(tenant_id: str, project_ref_id: str, env_name: str,
                           envelope: dict) -> dict[str, bool]:
    """Compare current node configs against deployed snapshots to detect changes (per D-10).

    Returns {node_name: is_modified} for each node in the envelope.
    """
    deployed = get_node_deploy_statuses(tenant_id, project_ref_id, env_name)
    result: dict[str, bool] = {}

    for node in envelope.get("nodes", []):
        node_name = node.get("name", "")
        config = node.get("config", {})
        current_hash = compute_config_hash(config)

        if node_name not in deployed:
            # Never deployed -- consider modified
            result[node_name] = True
            continue

        deployed_hash = deployed[node_name].get("config_hash", "")
        if current_hash != deployed_hash:
            result[node_name] = True
        else:
            result[node_name] = False

    return result
