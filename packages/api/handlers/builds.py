"""Build endpoints -- trigger container builds, check status, detect dirty state."""
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import builds as build_store
from packages.platform.gcp.cloud_build import (
    compute_image_uri,
    compute_source_hash,
    get_build_status as cb_get_build_status,
    submit_container_build,
)

log = logging.getLogger(__name__)
router = APIRouter()

COMPUTE_TYPES = {"cloud_run", "cloud_run_job", "cloud_function"}
BUILDABLE_MODES = {"workflow", "code_editor"}


# --- Static-segment routes MUST come before parameterized routes ---
# FastAPI matches routes in definition order. /batch and /status must be
# defined before /{node_name} to avoid "batch" being captured as a node name.


@router.post("/builds/{project_ref_id}/{env_name}/batch")
async def trigger_batch_build(
    project_ref_id: str, env_name: str,
    background_tasks: BackgroundTasks,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Trigger builds for all dirty compute nodes in parallel (per D-05)."""
    project = access.project
    owner_uid = access.owner_uid
    project_id = project.get("project_id", "")
    region = project.get("region", "us-central1")
    host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host-dev")

    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, env_name)
    if not blueprint or not blueprint.get("envelope"):
        raise HTTPException(status_code=404, detail="No blueprint found")

    envelope = blueprint["envelope"]
    results = []

    for node in envelope.get("nodes", []):
        if node.get("type") not in COMPUTE_TYPES:
            continue
        config = node.get("config", {})
        mode = config.get("mode", "workflow")
        if mode not in BUILDABLE_MODES:
            continue

        node_name = node["name"]
        image_uri = compute_image_uri(project_id, region, node_name)

        # Gather source files
        if mode == "workflow":
            from packages.core.codegen.code_generator import generate_compute_code
            global_config = envelope.get("global", {})
            all_nodes = envelope.get("nodes", []) + envelope.get("resources", [])
            generated = generate_compute_code(node, all_nodes, global_config)
            if not generated or not generated.files:
                results.append({"node_name": node_name, "status": "skipped", "reason": "code generation failed"})
                continue
            source_files = generated.files
        else:
            from packages.platform.gcp.storage import list_files, read_file
            file_list = list_files(project_id, env_name, node_name)
            source_files = {}
            for f in file_list:
                content = read_file(project_id, env_name, node_name, f["name"])
                if content is not None:
                    source_files[f["name"]] = content
            if not source_files:
                results.append({"node_name": node_name, "status": "skipped", "reason": "no source files"})
                continue

        source_hash = compute_source_hash(source_files)

        # Check dirty state (per D-07): skip if clean
        latest_build = build_store.get_latest_build_for_node(owner_uid, project_id, env_name, node_name)
        if latest_build and latest_build.get("status") == "success" and latest_build.get("source_hash") == source_hash:
            results.append({"node_name": node_name, "status": "clean", "image_uri": latest_build.get("image_uri", "")})
            continue

        build_record_id = build_store.create_build_record(owner_uid, project_id, env_name, node_name, {
            "image_uri": image_uri,
            "source_hash": source_hash,
        })

        background_tasks.add_task(
            _run_container_build,
            owner_uid, build_record_id, host_project_id, project_id,
            env_name, node_name, source_files, image_uri,
            project_ref_id,
        )

        results.append({"node_name": node_name, "build_record_id": build_record_id, "status": "queued", "image_uri": image_uri})

    return JSONResponse(status_code=202, content={"builds": results})


@router.get("/builds/{project_ref_id}/{env_name}/status")
async def get_builds_status(
    project_ref_id: str, env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Get build status for all compute nodes in an environment (per D-15)."""
    project = access.project
    owner_uid = access.owner_uid
    project_id = project.get("project_id", "")

    records = build_store.list_build_records(owner_uid, project_id, env_name)
    return {"builds": records}


# --- Parameterized routes (after static segments) ---


@router.post("/builds/{project_ref_id}/{env_name}/{node_name}")
async def trigger_build(
    project_ref_id: str, env_name: str, node_name: str,
    background_tasks: BackgroundTasks,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Trigger a container build for a single compute node (per D-01, D-03)."""
    project = access.project
    owner_uid = access.owner_uid
    project_id = project.get("project_id", "")
    region = project.get("region", "us-central1")
    host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host-dev")

    # Resolve node from blueprint
    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, env_name)
    if not blueprint or not blueprint.get("envelope"):
        raise HTTPException(status_code=404, detail="No blueprint found")

    envelope = blueprint["envelope"]
    node = None
    for n in envelope.get("nodes", []):
        if n.get("name") == node_name:
            node = n
            break
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")
    if node.get("type") not in COMPUTE_TYPES:
        raise HTTPException(status_code=422, detail=f"Node '{node_name}' is not a compute node")

    config = node.get("config", {})
    mode = config.get("mode", "workflow")
    log.info("trigger_build: node=%s type=%s mode=%s config_keys=%s", node_name, node.get("type"), mode, list(config.keys()))
    if mode not in BUILDABLE_MODES:
        raise HTTPException(status_code=422, detail=f"Node '{node_name}' uses {mode} mode -- no build needed")

    image_uri = compute_image_uri(project_id, region, node_name)

    # Gather source files based on mode (per D-02)
    if mode == "workflow":
        from packages.core.codegen.code_generator import generate_compute_code
        global_config = envelope.get("global", {})
        all_nodes = envelope.get("nodes", []) + envelope.get("resources", [])
        generated = generate_compute_code(node, all_nodes, global_config)
        if not generated or not generated.files:
            raise HTTPException(status_code=422, detail=f"Code generation failed for '{node_name}'")
        source_files = generated.files
    else:
        # code_editor mode: read files from GCS
        from packages.platform.gcp.storage import list_files, read_file
        file_list = list_files(project_id, env_name, node_name)
        source_files = {}
        for f in file_list:
            content = read_file(project_id, env_name, node_name, f["name"])
            if content is not None:
                source_files[f["name"]] = content
        if not source_files:
            raise HTTPException(status_code=422, detail=f"No source files found for '{node_name}'")

    source_hash = compute_source_hash(source_files)

    # Create build record in Firestore
    build_record_id = build_store.create_build_record(owner_uid, project_id, env_name, node_name, {
        "image_uri": image_uri,
        "source_hash": source_hash,
    })

    # Run build in background
    background_tasks.add_task(
        _run_container_build,
        owner_uid, build_record_id, host_project_id, project_id,
        env_name, node_name, source_files, image_uri,
        project_ref_id,
    )

    return JSONResponse(status_code=202, content={
        "build_record_id": build_record_id,
        "node_name": node_name,
        "status": "queued",
        "image_uri": image_uri,
    })


@router.get("/builds/{project_ref_id}/{env_name}/{node_name}/status")
async def get_node_build_status(
    project_ref_id: str, env_name: str, node_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Get build status for a specific node (per D-15)."""
    project = access.project
    owner_uid = access.owner_uid
    project_id = project.get("project_id", "")

    record = build_store.get_latest_build_for_node(owner_uid, project_id, env_name, node_name)
    if not record:
        return {"node_name": node_name, "status": "not_built"}
    return record


def _run_container_build(tenant_id, build_record_id, host_project_id, project_id,
                         env_name, node_name, source_files, image_uri,
                         project_ref_id=None):
    """Background task: submit Cloud Build and poll until completion."""
    import time

    try:
        build_store.update_build_record(tenant_id, build_record_id, status="building")

        result = submit_container_build(
            host_project_id=host_project_id,
            target_project_id=project_id,
            env_name=env_name,
            node_name=node_name,
            source_files=source_files,
            image_uri=image_uri,
        )

        build_id = result["build_id"]
        build_store.update_build_record(tenant_id, build_record_id,
                                  status="building", build_id=build_id,
                                  log_url=result.get("log_url"))

        # Poll until terminal
        terminal_states = {"SUCCESS", "FAILURE", "TIMEOUT", "CANCELLED", "EXPIRED"}
        while True:
            status = cb_get_build_status(host_project_id, build_id)
            if status["status"] in terminal_states:
                break
            time.sleep(10)

        if status["status"] == "SUCCESS":
            build_store.update_build_record(tenant_id, build_record_id,
                                      status="success", image_uri=image_uri)

            # Write built image URI back to the saved blueprint node
            if project_ref_id:
                _persist_image_to_blueprint(tenant_id, project_ref_id, env_name, node_name, image_uri)
        else:
            build_store.update_build_record(tenant_id, build_record_id,
                                      status="failed",
                                      error=f"Cloud Build {status['status']}")

    except Exception as e:
        log.exception("Build failed for %s/%s/%s", project_id, env_name, node_name)
        build_store.update_build_record(tenant_id, build_record_id,
                                  status="failed", error=str(e))


def _persist_image_to_blueprint(tenant_id, project_ref_id, env_name, node_name, image_uri):
    """Write built image URI into the blueprint node's config so it persists across saves.

    Nodes are keyed by slug in the subcollection (falling back to name).
    Try slug=name first, then scan nodes to find the right slug.
    """
    try:
        # Try name as slug (common case)
        node_data = blueprint_store.get_node(tenant_id, project_ref_id, env_name, node_name)
        slug = node_name

        # If not found by name, scan nodes to find the slug for this node_name
        if not node_data:
            all_nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
            for n in all_nodes:
                if n.get("name") == node_name:
                    slug = n.get("slug", node_name)
                    node_data = blueprint_store.get_node(tenant_id, project_ref_id, env_name, slug)
                    break

        if node_data:
            node_data.setdefault("config", {})["image"] = image_uri
            blueprint_store.save_node(tenant_id, project_ref_id, env_name, slug, node_data)
    except Exception as e:
        log.warning("Failed to persist image URI to blueprint for %s: %s", node_name, e)
