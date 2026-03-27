"""Container build MCP tools — trigger builds, check status, retrieve logs."""

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
build_store = None
cloud_build = None

COMPUTE_TYPES = {"cloud_run", "cloud_run_job", "cloud_function"}
BUILDABLE_MODES = {"workflow", "code_editor"}
TERMINAL_BUILD_STATUSES = {"success", "failed"}


def _ensure_deps():
    """Lazy-load dependencies to avoid import-time GCP SDK initialization."""
    global projects_store, blueprint_store, build_store, cloud_build
    if projects_store is None:
        from packages.platform.store import projects as _ps
        projects_store = _ps
    if blueprint_store is None:
        from packages.platform.store import blueprints as _bs
        blueprint_store = _bs
    if build_store is None:
        from packages.platform.store import builds as _bld
        build_store = _bld
    if cloud_build is None:
        from packages.platform.gcp import cloud_build as _cb
        cloud_build = _cb


def _resolve_project_and_env(project_ref_id: str, env_name: str):
    """Resolve project, env entry, and GCP project ID.

    Returns (tenant_id, project, env_entry, gcp_project_id, error_string).
    """
    _ensure_deps()
    tenant_id = get_tenant_id()

    project = projects_store.get_project(tenant_id, project_ref_id)
    if not project:
        return tenant_id, None, None, None, format_error("not_found", f"Project {project_ref_id} not found")

    env_entry = projects_store.get_env_entry(
        project.get("environments", []), env_name
    )
    if not env_entry:
        return tenant_id, project, None, None, format_error("not_found", f"Environment {env_name} not found")

    gcp_project_id = env_entry.get("gcp_project_id")
    if not gcp_project_id:
        return tenant_id, project, env_entry, None, format_error(
            "not_provisioned", f"Environment {env_name} has no GCP project ID"
        )

    return tenant_id, project, env_entry, gcp_project_id, None


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def trigger_build(
    project_ref_id: str,
    env_name: str,
    node_slug: str,
) -> str:
    """Trigger a container build for a compute node.

    Submits a Cloud Build job to build a Docker image from the node's source
    files and push to Artifact Registry. Checks for in-progress builds first.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        node_slug: The slug of the compute node to build.
    """
    try:
        _ensure_deps()
        tenant_id, project, env_entry, gcp_project_id, err = _resolve_project_and_env(
            project_ref_id, env_name
        )
        if err:
            return err

        project_id = project.get("project_id", "")

        # Check for in-progress builds (D-19 concurrency guard)
        try:
            latest_build = build_store.get_latest_build_for_node(
                tenant_id, project_id, env_name, node_slug
            )
        except Exception as guard_err:
            log.warning("Build concurrency check failed (index may be building): %s", guard_err)
            latest_build = None
        if latest_build and latest_build.get("status") not in TERMINAL_BUILD_STATUSES and latest_build.get("status") is not None:
            build_id = latest_build.get("id", "unknown")
            return format_error(
                "concurrency_conflict",
                f"Build blocked: build {build_id} already in progress for {node_slug}. "
                "Wait for completion or check status with get_build_status.",
            )

        # Resolve node from subcollection
        all_nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
        if not all_nodes:
            return format_error("not_found", "No nodes found in blueprint")

        node = None
        for n in all_nodes:
            if n.get("slug") == node_slug or n.get("name") == node_slug:
                node = n
                break
        if not node:
            return format_error("not_found", f"Node '{node_slug}' not found in blueprint")
        if node.get("type") not in COMPUTE_TYPES:
            return format_error("validation_error", f"Node '{node_slug}' is not a compute node")

        # Reconstruct envelope for code generation
        envelope = {
            "global": {"project_id": project_id, "region": project.get("region", "us-central1"), "environment": env_name},
            "nodes": all_nodes,
        }

        config = node.get("config", {})
        mode = config.get("mode", "workflow")
        if mode not in BUILDABLE_MODES:
            return format_error("validation_error", f"Node '{node_slug}' uses {mode} mode -- no build needed")

        region = project.get("region", env_entry.get("region", "us-central1"))
        node_name = node.get("name", node_slug)
        image_uri = cloud_build.compute_image_uri(project_id, region, node_name)
        host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host-dev")

        # Gather source files
        if mode == "workflow":
            from packages.core.codegen.code_generator import generate_compute_code
            global_config = envelope.get("global", {})
            all_nodes = envelope.get("nodes", []) + envelope.get("resources", [])
            generated = generate_compute_code(node, all_nodes, global_config)
            if not generated or not generated.files:
                return format_error("build_error", f"Code generation failed for '{node_slug}'")
            source_files = generated.files
        else:
            from packages.platform.gcp.storage import list_files, read_file
            # MCP write_code_file stores under project_ref_id + node_slug
            # Try that path first, fall back to project_id + node_name
            node_name = node.get("name", node_slug)
            file_list = list_files(project_ref_id, env_name, node_slug)
            if not file_list:
                file_list = list_files(project_id, env_name, node_name)
                gcs_proj, gcs_node = project_id, node_name
            else:
                gcs_proj, gcs_node = project_ref_id, node_slug
            source_files = {}
            for f in file_list:
                content = read_file(gcs_proj, env_name, gcs_node, f)
                if content is not None:
                    source_files[f] = content
            if not source_files:
                return format_error("build_error", f"No source files found for '{node_slug}'")

        source_hash = cloud_build.compute_source_hash(source_files)

        # Create build record
        build_record_id = build_store.create_build_record(
            tenant_id, project_id, env_name, node_name,
            {"image_uri": image_uri, "source_hash": source_hash},
        )

        # Run build in background thread (not BackgroundTasks since we're outside ASGI)
        from packages.api.handlers.builds import _run_container_build
        t = threading.Thread(
            target=_run_container_build,
            args=(tenant_id, build_record_id, host_project_id, project_id,
                  env_name, node_name, source_files, image_uri, project_ref_id),
            daemon=True,
        )
        t.start()

        return format_json_response({
            "build_record_id": build_record_id,
            "node_slug": node_slug,
            "status": "queued",
            "image_uri": image_uri,
        })
    except Exception as e:
        log.error("trigger_build failed: %s", e)
        return format_error("trigger_build_error", str(e))


@mcp.tool()
def get_build_status(
    project_ref_id: str,
    env_name: str,
    build_id: str,
) -> str:
    """Get the status of a container build.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        build_id: The build record ID to check.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()

        record = build_store.get_build_record(tenant_id, build_id)
        if not record:
            return format_error("not_found", f"Build record '{build_id}' not found")

        return format_json_response({
            "build_id": record.get("id", build_id),
            "status": record.get("status"),
            "node_name": record.get("node_name"),
            "image_uri": record.get("image_uri"),
            "log_url": record.get("log_url"),
            "error": record.get("error"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        })
    except Exception as e:
        log.error("get_build_status failed: %s", e)
        return format_error("get_build_status_error", str(e))


@mcp.tool()
def get_build_logs(
    project_ref_id: str,
    env_name: str,
    build_id: str,
) -> str:
    """Retrieve build output logs for a completed (or failed) build.

    Returns Terraform plan and apply output from GCS, plus the Cloud Build
    console log URL.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        build_id: The build record ID whose logs to retrieve.
    """
    try:
        _ensure_deps()
        tenant_id = get_tenant_id()
        host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host-dev")

        record = build_store.get_build_record(tenant_id, build_id)
        if not record:
            return format_error("not_found", f"Build record '{build_id}' not found")

        status = record.get("status", "unknown")
        log_url = record.get("log_url")
        cb_build_id = record.get("build_id")  # Cloud Build ID (different from record ID)

        # If build is still in progress, return status + log_url only
        if status not in TERMINAL_BUILD_STATUSES:
            return format_json_response({
                "build_id": build_id,
                "status": status,
                "log_url": log_url,
                "message": "Build still in progress. Logs available after completion.",
            })

        # Fetch plan/apply output from GCS
        plan_output = None
        apply_output = None
        if cb_build_id:
            plan_output = cloud_build.get_build_plan_output(host_project_id, cb_build_id)
            apply_output = cloud_build.get_build_apply_output(host_project_id, cb_build_id)

        return format_json_response({
            "build_id": build_id,
            "status": status,
            "log_url": log_url,
            "plan_output": plan_output,
            "apply_output": apply_output,
        })
    except Exception as e:
        log.error("get_build_logs failed: %s", e)
        return format_error("get_build_logs_error", str(e))


@mcp.tool()
def list_builds(
    project_ref_id: str,
    env_name: str = "dev",
) -> str:
    """List container build records for a project environment.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment to list builds for (default: "dev").
    """
    try:
        _ensure_deps()
        tenant_id, project, env_entry, gcp_project_id, err = _resolve_project_and_env(
            project_ref_id, env_name
        )
        if err:
            return err

        project_id = project.get("project_id", "")
        records = build_store.list_build_records(tenant_id, project_id, env_name)

        builds = []
        for rec in records:
            builds.append({
                "build_id": rec.get("id"),
                "node_name": rec.get("node_name"),
                "status": rec.get("status"),
                "image_uri": rec.get("image_uri"),
                "created_at": rec.get("created_at"),
            })

        return format_json_response({
            "build_count": len(builds),
            "builds": builds,
        })
    except Exception as e:
        log.error("list_builds failed: %s", e)
        return format_error("list_builds_error", str(e))
