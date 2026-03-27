"""Project lifecycle MCP tools — list, inspect, and select projects and environments."""

import logging

from packages.mcp.server import mcp
from packages.mcp.context import get_tenant_id
from packages.mcp.tools.formatters import format_json_response, format_error, format_list

log = logging.getLogger(__name__)


# ── Pure logic (testable without store) ──────────────────────


def _get_env_entry(environments: list[dict], env_name: str) -> dict | None:
    """Find an environment entry by name from the environments list."""
    for env in environments:
        if isinstance(env, dict) and env.get("name") == env_name:
            return env
    return None


def _list_projects_impl(projects: list[dict]) -> str:
    """Format project list for MCP response."""
    return format_list(
        projects,
        fields=["display_name", "id", "provision_status"],
        title="Projects",
    )


def _get_available_actions(env_entry: dict | None, validation: dict | None, node_count: int) -> list[str]:
    """Determine available actions based on project state."""
    actions = []
    if env_entry:
        provision_status = env_entry.get("provision_status", "")
        if provision_status == "ready":
            actions.append("add_node")
            actions.append("validate")
            if node_count > 0:
                errors = (validation or {}).get("errors", 0)
                if errors == 0:
                    actions.append("deploy")
                else:
                    actions.append("fix_validation_errors")
    return actions


def _get_project_status_impl(
    project: dict,
    env_name: str,
    validation: dict | None,
    nodes: list[dict],
) -> str:
    """Format project status for MCP response."""
    environments = project.get("environments", [])
    env_entry = _get_env_entry(environments, env_name)

    node_count = len(nodes)
    errors = (validation or {}).get("errors", 0)
    warnings = (validation or {}).get("warnings", 0)
    actions = _get_available_actions(env_entry, validation, node_count)

    status = {
        "project_name": project.get("display_name", project.get("name", "Unknown")),
        "project_id": project.get("id", ""),
        "environment": env_name,
        "gcp_project_id": env_entry.get("gcp_project_id", "N/A") if env_entry else "N/A",
        "provision_status": env_entry.get("provision_status", "unknown") if env_entry else "no env",
        "environments": [e.get("name", "") for e in environments if isinstance(e, dict)],
        "node_count": node_count,
        "validation": {"errors": errors, "warnings": warnings},
        "actions": actions,
    }

    if errors > 0:
        status["hint"] = "Fix validation errors before deploying."

    return format_json_response(status)


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def list_projects() -> str:
    """List all projects for the current tenant.

    Returns a formatted list of projects with their display name, ID,
    and provisioning status.
    """
    try:
        from packages.platform.store import projects as projects_store
        tenant_id = get_tenant_id()
        projects = projects_store.list_projects(tenant_id)

        # Extract provision_status from first env for summary
        for p in projects:
            envs = p.get("environments", [])
            if envs and isinstance(envs[0], dict):
                p.setdefault("provision_status", envs[0].get("provision_status", "unknown"))
            else:
                p.setdefault("provision_status", "unknown")

        return _list_projects_impl(projects)
    except Exception as e:
        log.error("list_projects failed: %s", e)
        return format_error("list_projects_error", str(e))


@mcp.tool()
def get_project_status(project_ref_id: str, env_name: str = "dev") -> str:
    """Get detailed project status including environment info, node count, and available actions.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to inspect (default: "dev").

    Returns project name, GCP project ID, provision status, environment list,
    node count, validation error/warning counts, and available actions.
    """
    try:
        from packages.platform.store import projects as projects_store
        from packages.platform.store import blueprints as blueprint_store

        tenant_id = get_tenant_id()
        project = projects_store.get_project(tenant_id, project_ref_id)
        if not project:
            return format_error("not_found", f"Project '{project_ref_id}' not found")

        nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
        validation = blueprint_store.get_validation_doc(tenant_id, project_ref_id, env_name)

        return _get_project_status_impl(project, env_name, validation, nodes)
    except Exception as e:
        log.error("get_project_status failed: %s", e)
        return format_error("get_project_status_error", str(e))


@mcp.tool()
def select_environment(project_ref_id: str, env_name: str) -> str:
    """Get details for a specific project environment.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment name (e.g., "dev", "staging", "prod").

    Returns environment details including GCP project ID, provision status,
    and Terraform state bucket.
    """
    try:
        from packages.platform.store import projects as projects_store

        tenant_id = get_tenant_id()
        project = projects_store.get_project(tenant_id, project_ref_id)
        if not project:
            return format_error("not_found", f"Project '{project_ref_id}' not found")

        environments = project.get("environments", [])
        env_entry = _get_env_entry(environments, env_name)
        if not env_entry:
            available = [e.get("name", "") for e in environments if isinstance(e, dict)]
            return format_error(
                "not_found",
                f"Environment '{env_name}' not found",
                details={"available_environments": available},
            )

        return format_json_response({
            "environment": env_name,
            "gcp_project_id": env_entry.get("gcp_project_id", "N/A"),
            "provision_status": env_entry.get("provision_status", "unknown"),
            "tf_bucket": env_entry.get("tf_bucket", "N/A"),
        })
    except Exception as e:
        log.error("select_environment failed: %s", e)
        return format_error("select_environment_error", str(e))
