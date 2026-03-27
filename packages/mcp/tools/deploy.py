"""Deploy operation MCP tools — trigger deploys, check status, retrieve logs."""

import logging
import os
import threading

from packages.mcp.server import mcp
from packages.mcp.context import get_tenant_id
from packages.mcp.tools.formatters import format_json_response, format_error

log = logging.getLogger(__name__)

# Module-level references for lazy-loaded dependencies (testable via patch)
projects_store = None
blueprint_store = None
deploy_store = None

IN_PROGRESS_DEPLOY_STATUSES = {"pending", "generating", "building"}


def _ensure_deps():
    """Lazy-load dependencies to avoid import-time GCP SDK initialization."""
    global projects_store, blueprint_store, deploy_store
    if projects_store is None:
        from packages.platform.store import projects as _ps
        projects_store = _ps
    if blueprint_store is None:
        from packages.platform.store import blueprints as _bs
        blueprint_store = _bs
    if deploy_store is None:
        from packages.platform.store import deploys as _ds
        deploy_store = _ds


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def trigger_deploy(
    project_ref_id: str,
    env_name: str = "dev",
) -> str:
    """Trigger a full infrastructure deploy for an environment.

    Validates the blueprint, checks provisioning status, ensures no deploy is
    already in progress, then launches the deploy orchestrator in a background
    thread.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to deploy (default: "dev").
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        project = projects_store.get_project(tenant_id, project_ref_id)
        if not project:
            return format_error("not_found", f"Project {project_ref_id} not found")

        envs = project.get("environments", [])

        # Find env entry
        env_entry = projects_store.get_env_entry(envs, env_name)
        if not env_entry:
            return format_error("not_found", f"Environment '{env_name}' not found")

        # Provisioning guard (D-19)
        provision_status = env_entry.get("provision_status", "")
        if provision_status != "ready":
            return format_error(
                "deploy_blocked",
                f"Deploy blocked: environment '{env_name}' is not provisioned "
                f"(status: {provision_status}). Provision the environment first.",
            )

        gcp_project_id = env_entry.get("gcp_project_id", "")
        if not gcp_project_id:
            return format_error(
                "deploy_blocked",
                f"Deploy blocked: environment '{env_name}' has no GCP project ID.",
            )

        # Validation gate (D-21)
        blueprint = blueprint_store.get_env_blueprint(tenant_id, project_ref_id, env_name)
        if blueprint and blueprint.get("envelope"):
            from packages.core.schemas.base import Envelope
            from packages.core.validation import validate_blueprint

            env_envelope = Envelope.model_validate(blueprint["envelope"])
            issues = validate_blueprint(env_envelope)
            error_issues = [i for i in issues if i.severity == "error"]
            if error_issues:
                error_count = len(error_issues)
                blocked_nodes = sorted(set(i.node for i in error_issues if i.node))
                return format_error(
                    "validation_errors",
                    f"Deploy blocked: blueprint has {error_count} validation error(s). "
                    "Fix errors before deploying.",
                    details={
                        "error_count": error_count,
                        "blocked_nodes": blocked_nodes,
                        "errors": [{"node": i.node, "message": i.message} for i in error_issues],
                    },
                )

        # Concurrency guard (D-19) -- check for in-progress deploy
        existing_deploys = deploy_store.list_deploys(tenant_id, project_ref_id, limit=5)
        for dep in existing_deploys:
            if dep.get("env_name") == env_name and dep.get("status") in IN_PROGRESS_DEPLOY_STATUSES:
                deploy_id = dep.get("id", "unknown")
                return format_error(
                    "concurrency_conflict",
                    f"Deploy blocked: deploy {deploy_id} in progress for '{env_name}'. "
                    "Check status with get_deploy_status.",
                )

        # Create deploy record
        region = env_entry.get("region", "us-central1")
        tf_bucket = os.environ.get(
            "TF_STATE_BUCKET",
            f"{os.environ.get('GCP_PROJECT_ID', 'pl4m-host-dev')}-tfstate",
        )

        deploy_id = deploy_store.create_deploy_record(
            tenant_id, gcp_project_id, env_name,
            {"project_ref_id": project_ref_id, "region": region, "tf_bucket": tf_bucket},
        )

        # Launch deploy orchestrator in background thread
        from packages.platform.deploy_orchestrator import _run_deploy
        t = threading.Thread(
            target=_run_deploy,
            args=(tenant_id, deploy_id, project_ref_id, gcp_project_id,
                  env_name, region, tf_bucket),
            daemon=True,
        )
        t.start()

        return format_json_response({
            "deploy_id": deploy_id,
            "status": "pending",
            "env_name": env_name,
            "message": f"Deploy started for environment '{env_name}'",
        })
    except Exception as e:
        log.error("trigger_deploy failed: %s", e)
        return format_error("trigger_deploy_error", str(e))


@mcp.tool()
def get_deploy_status(deploy_id: str) -> str:
    """Get the current status of a deploy operation.

    Args:
        deploy_id: The deploy record ID to check.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        status = deploy_store.get_deploy_status(tenant_id, deploy_id)
        if not status:
            return format_error("not_found", f"Deploy '{deploy_id}' not found")

        return format_json_response({
            "deploy_id": status.get("id", deploy_id),
            "status": status.get("status"),
            "env_name": status.get("env_name"),
            "error": status.get("error"),
            "created_at": status.get("created_at"),
            "updated_at": status.get("updated_at"),
            "build_id": status.get("build_id"),
            "log_url": status.get("log_url"),
        })
    except Exception as e:
        log.error("get_deploy_status failed: %s", e)
        return format_error("get_deploy_status_error", str(e))


@mcp.tool()
def get_deploy_logs(deploy_id: str) -> str:
    """Retrieve deploy logs including Terraform plan and apply output.

    Since MCP tools cannot stream SSE, this returns the stored log output
    from the deploy record.

    Args:
        deploy_id: The deploy record ID whose logs to retrieve.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        status = deploy_store.get_deploy_status(tenant_id, deploy_id)
        if not status:
            return format_error("not_found", f"Deploy '{deploy_id}' not found")

        deploy_status = status.get("status", "unknown")

        # If deploy is in progress, return status only
        if deploy_status in IN_PROGRESS_DEPLOY_STATUSES:
            return format_json_response({
                "deploy_id": deploy_id,
                "status": deploy_status,
                "log_url": status.get("log_url"),
                "message": "Deploy still in progress. Logs available after completion.",
                "steps": status.get("steps", []),
            })

        return format_json_response({
            "deploy_id": deploy_id,
            "status": deploy_status,
            "log_url": status.get("log_url"),
            "plan_output": status.get("plan_output"),
            "apply_output": status.get("apply_output"),
            "error": status.get("error"),
            "steps": status.get("steps", []),
        })
    except Exception as e:
        log.error("get_deploy_logs failed: %s", e)
        return format_error("get_deploy_logs_error", str(e))


@mcp.tool()
def list_deploys(
    project_ref_id: str,
    env_name: str | None = None,
) -> str:
    """List deploy records for a project, optionally filtered by environment.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: Optional environment name to filter by.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        records = deploy_store.list_deploys(tenant_id, project_ref_id)

        # Filter by env if specified
        if env_name:
            records = [r for r in records if r.get("env_name") == env_name]

        deploys = []
        for rec in records:
            deploys.append({
                "deploy_id": rec.get("id"),
                "env_name": rec.get("env_name"),
                "status": rec.get("status"),
                "created_at": rec.get("created_at"),
                "error": rec.get("error"),
            })

        return format_json_response({
            "deploy_count": len(deploys),
            "deploys": deploys,
        })
    except Exception as e:
        log.error("list_deploys failed: %s", e)
        return format_error("list_deploys_error", str(e))
