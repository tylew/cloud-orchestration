"""Node CRUD MCP tools with auto-provisioning integration."""

import logging
import random
import string
from datetime import datetime, timezone

from packages.mcp.server import mcp
from packages.mcp.context import get_tenant_id
from packages.mcp.tools.formatters import format_json_response, format_error

log = logging.getLogger(__name__)

# Module-level references for lazy-loaded dependencies (testable via patch)
blueprint_store = None
auto_provision_for_node = None
infer_iam_roles = None


def _ensure_deps():
    """Lazy-load dependencies to avoid import-time GCP SDK initialization."""
    global blueprint_store, auto_provision_for_node, infer_iam_roles
    if blueprint_store is None:
        from packages.platform.store import blueprints as _bs
        blueprint_store = _bs
    if auto_provision_for_node is None:
        from packages.core.auto_provision import auto_provision_for_node as _ap
        auto_provision_for_node = _ap
    if infer_iam_roles is None:
        from packages.core.iam_mappings import infer_iam_roles as _ir
        infer_iam_roles = _ir


# Slug prefix map (copied from packages/api/handlers/nodes.py)
_SLUG_PREFIXES = {
    "cloud_run": "cr", "cloud_run_job": "cj", "cloud_function": "cf",
    "service_account": "sa", "vpc": "vp", "subnet": "sn",
    "vpc_connector": "vc", "secret_manager": "sm", "gcs_bucket": "gs",
    "cloud_sql": "sq", "firestore": "fs", "bigquery": "bq",
    "bigtable": "bt", "pubsub_schema": "ps", "pubsub_topic": "pt",
    "pubsub_subscription": "pb", "cloud_task_queue": "tq",
    "external_lb": "lb", "third_party_api": "tp",
    "firestore_collection": "fc", "bigquery_table": "bqt",
    "cloud_sql_database": "sd", "cloud_sql_table": "st",
}

# Valid node types for add_node
_VALID_NODE_TYPES = set(_SLUG_PREFIXES.keys())


def _generate_slug(node_type: str) -> str:
    """Generate a unique slug with type-based prefix and random suffix."""
    prefix = _SLUG_PREFIXES.get(node_type, "nd")
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


def _run_validation_and_persist(
    tenant_id: str, project_ref_id: str, env_name: str
) -> dict[str, dict]:
    """Load all nodes, run validation, persist results, return per-slug dict."""
    _ensure_deps()
    all_node_dicts = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)

    try:
        from packages.core.schemas.base import Envelope
        from packages.core.validation import validate_blueprint_by_slug

        envelope = Envelope.model_validate({
            "global": {"project_id": "validation", "region": "us-central1", "environment": "dev"},
            "nodes": all_node_dicts,
        })
        validation = validate_blueprint_by_slug(envelope)
        blueprint_store.save_validation_doc(tenant_id, project_ref_id, env_name, {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "nodes": validation,
        })
        return validation
    except Exception as e:
        log.warning("Validation failed: %s", e)
        return {}


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def add_node(
    project_ref_id: str,
    env_name: str,
    name: str,
    node_type: str,
    config: dict | None = None,
    depends_on: list[str] | None = None,
) -> str:
    """Add a new resource node to a project blueprint.

    Auto-provisions supporting resources (service accounts, networking) for
    compute nodes. Returns the created node plus any auto-created nodes.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev", "staging", "prod").
        name: Human-readable name for the node.
        node_type: The GCP resource type (e.g., "cloud_run", "firestore").
        config: Optional resource-specific configuration.
        depends_on: Optional list of node slugs this node depends on.
    """
    try:
        # Validate node type early
        if node_type not in _VALID_NODE_TYPES:
            return format_error(
                "validation_error",
                f"Invalid node type '{node_type}'",
                details={"valid_types": sorted(_VALID_NODE_TYPES)},
            )

        _ensure_deps()
        tenant_id = get_tenant_id()
        slug = _generate_slug(node_type)

        # Build node dict
        node_dict = {
            "slug": slug,
            "name": name,
            "type": node_type,
            "config": config or {},
            "depends_on": depends_on or [],
        }

        # Check slug uniqueness
        if blueprint_store.get_node(tenant_id, project_ref_id, env_name, slug):
            slug = _generate_slug(node_type)
            node_dict["slug"] = slug

        # Persist primary node
        blueprint_store.save_node(tenant_id, project_ref_id, env_name, slug, node_dict)

        # Auto-provision supporting resources
        existing_nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
        provision_result = auto_provision_for_node(node_dict, existing_nodes)

        auto_created = []
        for auto_node in provision_result.get("created", []):
            auto_slug = auto_node.get("slug") or _generate_slug(auto_node["type"])
            auto_node["slug"] = auto_slug
            auto_node["auto_provisioned"] = True
            blueprint_store.save_node(
                tenant_id, project_ref_id, env_name, auto_slug, auto_node
            )
            auto_created.append(auto_node)

        # Update primary node if depends_on was modified by auto_provision
        if node_dict.get("depends_on") != (depends_on or []):
            blueprint_store.save_node(
                tenant_id, project_ref_id, env_name, slug, node_dict
            )

        # Run validation (D-21)
        validation = _run_validation_and_persist(tenant_id, project_ref_id, env_name)

        return format_json_response({
            "node": node_dict,
            "auto_created": auto_created,
            "validation": validation,
            "warnings": provision_result.get("warnings", []),
        })
    except Exception as e:
        log.error("add_node failed: %s", e)
        return format_error("add_node_error", str(e))


@mcp.tool()
def update_node(
    project_ref_id: str,
    env_name: str,
    slug: str,
    config: dict | None = None,
    depends_on: list[str] | None = None,
    name: str | None = None,
) -> str:
    """Update an existing node's configuration, dependencies, or name.

    Recomputes IAM roles when dependencies change. Runs validation after update.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        slug: The slug of the node to update.
        config: Optional new configuration (merged with existing).
        depends_on: Optional new dependency list (replaces existing).
        name: Optional new name for the node.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        existing = blueprint_store.get_node(tenant_id, project_ref_id, env_name, slug)
        if not existing:
            return format_error("not_found", f"Node '{slug}' not found")

        # Merge updates
        if config is not None:
            existing["config"] = {**existing.get("config", {}), **config}
        if depends_on is not None:
            existing["depends_on"] = depends_on
        if name is not None:
            existing["name"] = name

        # Recompute IAM roles if depends_on changed
        if depends_on is not None:
            all_nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
            roles = infer_iam_roles(existing, all_nodes)
            if roles:
                iam = existing.get("iam", {})
                iam["roles"] = sorted(roles)
                existing["iam"] = iam

        # Persist
        blueprint_store.save_node(tenant_id, project_ref_id, env_name, slug, existing)

        # Run validation (D-21)
        validation = _run_validation_and_persist(tenant_id, project_ref_id, env_name)

        return format_json_response({
            "node": existing,
            "validation": validation,
        })
    except Exception as e:
        log.error("update_node failed: %s", e)
        return format_error("update_node_error", str(e))


@mcp.tool()
def delete_node(
    project_ref_id: str,
    env_name: str,
    slug: str,
) -> str:
    """Delete a node from the blueprint. Cascades to children.

    Warns if deleting an auto-provisioned node (per D-10) since it may
    break compute nodes that depend on it.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        slug: The slug of the node to delete.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()
        warnings = []

        # Check if auto-provisioned (D-10)
        existing = blueprint_store.get_node(tenant_id, project_ref_id, env_name, slug)
        if existing and existing.get("auto_provisioned"):
            warnings.append(
                f"Node '{slug}' was auto-provisioned. Deleting it may break "
                "compute nodes that depend on it."
            )

        # Delete node + children
        deleted_slugs = blueprint_store.delete_node(
            tenant_id, project_ref_id, env_name, slug
        )

        # Run validation (D-21)
        validation = _run_validation_and_persist(tenant_id, project_ref_id, env_name)

        return format_json_response({
            "deleted_slugs": deleted_slugs,
            "validation": validation,
            "warnings": warnings,
        })
    except Exception as e:
        log.error("delete_node failed: %s", e)
        return format_error("delete_node_error", str(e))


@mcp.tool()
def list_nodes(project_ref_id: str, env_name: str = "dev") -> str:
    """List all nodes in a project blueprint with validation state.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to inspect (default: "dev").

    Returns each node's slug, type, name, validation status, and
    whether it was auto-provisioned.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
        validation_doc = blueprint_store.get_validation_doc(
            tenant_id, project_ref_id, env_name
        )
        validation_nodes = (validation_doc or {}).get("nodes", {})

        result_nodes = []
        for n in nodes:
            slug = n.get("slug", n.get("name", ""))
            node_validation = validation_nodes.get(slug, {})
            errors = node_validation.get("errors", [])
            warnings = node_validation.get("warnings", [])
            result_nodes.append({
                "slug": slug,
                "name": n.get("name", ""),
                "type": n.get("type", ""),
                "auto_provisioned": n.get("auto_provisioned", False),
                "validation": {
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                },
            })

        return format_json_response({
            "node_count": len(result_nodes),
            "nodes": result_nodes,
        })
    except Exception as e:
        log.error("list_nodes failed: %s", e)
        return format_error("list_nodes_error", str(e))
