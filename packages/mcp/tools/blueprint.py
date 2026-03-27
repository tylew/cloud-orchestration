"""Blueprint and Terraform MCP tools — inspect, validate, and preview infrastructure."""

import logging

from packages.mcp.server import mcp
from packages.mcp.context import get_tenant_id
from packages.mcp.tools.formatters import format_json_response, format_error

log = logging.getLogger(__name__)


# ── Pure logic (testable without store/core dependencies) ────


def _get_blueprint_impl(nodes: list[dict]) -> str:
    """Format blueprint summary for MCP response."""
    summary = {
        "node_count": len(nodes),
        "nodes": [
            {
                "slug": n.get("slug", n.get("name", "")),
                "name": n.get("name", ""),
                "type": n.get("type", ""),
            }
            for n in nodes
        ],
    }
    return format_json_response(summary)


def _validate_blueprint_impl(issues: list[dict]) -> str:
    """Format validation results for MCP response."""
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    result = {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": [{"node": i.get("node"), "message": i.get("message")} for i in errors],
        "warnings": [{"node": i.get("node"), "message": i.get("message")} for i in warnings],
    }
    return format_json_response(result)


def _preview_terraform_impl(tf_files: dict[str, str], max_chars: int = 2000) -> str:
    """Format Terraform preview for MCP response."""
    files = {}
    for filename, content in tf_files.items():
        if len(content) > max_chars:
            files[filename] = content[:max_chars] + f"\n... (truncated, {len(content)} total chars)"
        else:
            files[filename] = content
    result = {
        "file_count": len(tf_files),
        "files": files,
    }
    return format_json_response(result)


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def get_blueprint(project_ref_id: str, env_name: str = "dev") -> str:
    """Get the blueprint for a project environment, listing all nodes.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to inspect (default: "dev").

    Returns a summary with node count and list of nodes (slug, name, type).
    """
    try:
        from packages.platform.store import blueprints as blueprint_store

        tenant_id = get_tenant_id()
        nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
        return _get_blueprint_impl(nodes)
    except Exception as e:
        log.error("get_blueprint failed: %s", e)
        return format_error("get_blueprint_error", str(e))


@mcp.tool()
def validate_blueprint(project_ref_id: str, env_name: str = "dev") -> str:
    """Run validation on a project blueprint and return results.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to validate (default: "dev").

    Loads nodes, builds an Envelope, and runs the full validation pipeline.
    Returns valid/invalid status, error and warning counts, and per-node issues.
    """
    try:
        from packages.platform.store import blueprints as blueprint_store
        from packages.core.schemas.base import Envelope
        from packages.core.validation import validate_blueprint as run_validation

        tenant_id = get_tenant_id()
        bp = blueprint_store.get_env_blueprint(tenant_id, project_ref_id, env_name)
        if not bp:
            return format_error("not_found", f"No blueprint found for env '{env_name}'")

        envelope = Envelope.model_validate(bp["envelope"])
        issues = run_validation(envelope)
        issue_dicts = [
            {"severity": i.severity, "node": i.node, "message": i.message}
            for i in issues
        ]
        return _validate_blueprint_impl(issue_dicts)
    except Exception as e:
        log.error("validate_blueprint failed: %s", e)
        return format_error("validate_blueprint_error", str(e))


@mcp.tool()
def preview_terraform(project_ref_id: str, env_name: str = "dev") -> str:
    """Preview generated Terraform files for a project blueprint.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to preview (default: "dev").

    Loads nodes, builds an Envelope, and generates Terraform HCL.
    Returns the list of generated file names and their contents
    (truncated if >2000 chars per file).
    """
    try:
        from packages.platform.store import blueprints as blueprint_store
        from packages.core.schemas.base import Envelope
        from packages.core.terraform.generator import generate_terraform

        tenant_id = get_tenant_id()
        bp = blueprint_store.get_env_blueprint(tenant_id, project_ref_id, env_name)
        if not bp:
            return format_error("not_found", f"No blueprint found for env '{env_name}'")

        envelope = Envelope.model_validate(bp["envelope"])
        tf_files = generate_terraform(envelope)
        return _preview_terraform_impl(tf_files)
    except Exception as e:
        log.error("preview_terraform failed: %s", e)
        return format_error("preview_terraform_error", str(e))


@mcp.tool()
def get_validation_status(project_ref_id: str, env_name: str = "dev") -> str:
    """Get the persisted validation status for a project blueprint.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to check (default: "dev").

    Returns the last persisted validation results from Firestore
    without re-running validation. Quick check for current state.
    """
    try:
        from packages.platform.store import blueprints as blueprint_store

        tenant_id = get_tenant_id()
        validation = blueprint_store.get_validation_doc(tenant_id, project_ref_id, env_name)
        if not validation:
            return format_error("not_found", f"No validation results for env '{env_name}'")
        return format_json_response(validation)
    except Exception as e:
        log.error("get_validation_status failed: %s", e)
        return format_error("get_validation_status_error", str(e))
