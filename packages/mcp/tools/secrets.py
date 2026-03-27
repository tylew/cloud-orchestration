"""Secret management MCP tools — create, list, get, delete secrets."""

import logging

from packages.mcp.server import mcp
from packages.mcp.context import get_tenant_id, get_current_user
from packages.mcp.tools.formatters import format_json_response, format_error

log = logging.getLogger(__name__)

# Module-level references for lazy-loaded dependencies (testable via patch)
projects_store = None
secrets_store = None
gcp_sm = None


def _ensure_deps():
    """Lazy-load dependencies to avoid import-time GCP SDK initialization."""
    global projects_store, secrets_store, gcp_sm
    if projects_store is None:
        from packages.platform.store import projects as _ps
        projects_store = _ps
    if secrets_store is None:
        from packages.platform.store import secrets as _ss
        secrets_store = _ss
    if gcp_sm is None:
        from packages.platform.gcp import secret_manager as _sm
        gcp_sm = _sm


def _resolve_gcp_project(project_ref_id: str, env_name: str) -> tuple[dict | None, dict | None, str | None]:
    """Resolve project and GCP project ID from env entry.

    Returns (project, env_entry, error_string).
    If error_string is not None, the caller should return it.
    """
    _ensure_deps()
    tenant_id = get_tenant_id()

    project = projects_store.get_project(tenant_id, project_ref_id)
    if not project:
        return None, None, format_error("not_found", f"Project {project_ref_id} not found")

    env_entry = projects_store.get_env_entry(
        project.get("environments", []), env_name
    )
    if not env_entry:
        return project, None, format_error("not_found", f"Environment {env_name} not found")

    gcp_project_id = env_entry.get("gcp_project_id")
    if not gcp_project_id:
        return project, env_entry, format_error(
            "not_provisioned", f"Environment {env_name} has no GCP project ID"
        )

    return project, env_entry, None


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def create_secret(
    project_ref_id: str,
    env_name: str,
    secret_name: str,
    secret_value: str,
    description: str = "",
) -> str:
    """Create a new secret in Secret Manager and save metadata to Firestore.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev", "staging", "prod").
        secret_name: Name/ID for the secret (e.g., "DB_PASSWORD").
        secret_value: The secret value to store. NOT echoed in response.
        description: Optional description of the secret's purpose.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()
        user = get_current_user()

        project, env_entry, err = _resolve_gcp_project(project_ref_id, env_name)
        if err:
            return err
        gcp_project_id = env_entry.get("gcp_project_id")

        result = secrets_store.create_secret(
            tenant_id, project_ref_id, env_name,
            gcp_project_id, secret_name, secret_value,
            description, user.email,
        )

        # Return confirmation WITHOUT the secret value
        return format_json_response({
            "secret_id": result.get("secret_id", secret_name),
            "version": result.get("version"),
            "status": result.get("status", "active"),
            "message": f"Secret '{secret_name}' created successfully",
        })
    except Exception as e:
        log.error("create_secret failed: %s", e)
        return format_error("create_secret_error", str(e))


@mcp.tool()
def list_secrets(project_ref_id: str, env_name: str = "dev") -> str:
    """List all secrets for a project environment.

    Returns secret names and metadata (values are never exposed in listings).

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to list secrets for (default: "dev").
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        secrets = secrets_store.list_secrets(tenant_id, project_ref_id, env_name)
        return format_json_response({"secrets": secrets})
    except Exception as e:
        log.error("list_secrets failed: %s", e)
        return format_error("list_secrets_error", str(e))


@mcp.tool()
def get_secret(
    project_ref_id: str,
    env_name: str,
    secret_name: str,
) -> str:
    """Get a secret's value from Secret Manager.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        secret_name: The secret name/ID to retrieve.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        # Get metadata from Firestore
        secret_meta = secrets_store.get_secret(tenant_id, project_ref_id, env_name, secret_name)
        if not secret_meta:
            return format_error("not_found", f"Secret '{secret_name}' not found")

        # Get actual value from GCP Secret Manager
        project, env_entry, err = _resolve_gcp_project(project_ref_id, env_name)
        if err:
            return err
        gcp_project_id = env_entry.get("gcp_project_id")

        value = gcp_sm.get_secret_value(gcp_project_id, secret_name)

        return format_json_response({
            "secret_id": secret_name,
            "value": value,
            "status": secret_meta.get("status", "unknown"),
        })
    except Exception as e:
        log.error("get_secret failed: %s", e)
        return format_error("get_secret_error", str(e))


@mcp.tool()
def delete_secret(
    project_ref_id: str,
    env_name: str,
    secret_name: str,
) -> str:
    """Delete a secret from Secret Manager and Firestore.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        secret_name: The secret name/ID to delete.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        project, env_entry, err = _resolve_gcp_project(project_ref_id, env_name)
        if err:
            return err
        gcp_project_id = env_entry.get("gcp_project_id")

        result = secrets_store.delete_secret(
            tenant_id, project_ref_id, env_name,
            gcp_project_id, secret_name,
        )

        return format_json_response({
            "secret_id": secret_name,
            "status": result.get("status", "destroyed"),
            "message": f"Secret '{secret_name}' deleted",
        })
    except Exception as e:
        log.error("delete_secret failed: %s", e)
        return format_error("delete_secret_error", str(e))
