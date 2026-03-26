"""Project reference CRUD for multi-tenant blueprint targeting."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import projects as project_store
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import deploys as deploy_store
from packages.platform.store import collaborators as collab_store
from packages.platform.deploy_orchestrator import _run_deploy

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects")
async def create_project(payload: dict, user: CurrentUser = Depends(get_current_user)):
    required = {"project_id", "display_name", "region"}
    missing = required - set(payload.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {', '.join(missing)}")

    result = project_store.save_project(user.tenant_id, {
        "project_id": payload["project_id"],
        "display_name": payload["display_name"],
        "region": payload.get("region", "us-central1"),
        "environments": payload.get("environments") or ["prod"],
    })
    return result


@router.get("/projects/{project_ref_id}")
async def get_project(access: ProjectAccess = Depends(require_project_access("viewer"))):
    return access.project


@router.get("/projects")
async def list_projects(user: CurrentUser = Depends(get_current_user)):
    return project_store.list_projects(user.tenant_id)


@router.delete("/projects/{project_ref_id}")
async def delete_project(project_ref_id: str, access: ProjectAccess = Depends(require_project_access("admin"))):
    # Only owner can delete — admin collaborators cannot
    if access.user.tenant_id != access.owner_uid and not access.user.is_admin:
        raise HTTPException(status_code=404, detail="Project not found")
    deleted = project_store.delete_project(access.owner_uid, project_ref_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


@router.patch("/projects/{project_ref_id}")
async def update_project_settings(project_ref_id: str, payload: dict,
                                   access: ProjectAccess = Depends(require_project_access("editor"))):
    try:
        result = project_store.update_project_settings(access.owner_uid, project_ref_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.post("/projects/{project_ref_id}/envs/{env_name}/deploy")
async def deploy_env(project_ref_id: str, env_name: str, background_tasks: BackgroundTasks,
                     access: ProjectAccess = Depends(require_project_access("admin"))):
    project = access.project
    owner_uid = access.owner_uid

    envs = project.get("environments", [])
    # Find env
    env_obj = None
    env_idx = -1
    for i, e in enumerate(envs):
        if isinstance(e, dict) and e.get("name") == env_name:
            env_obj = e
            env_idx = i
            break
        elif isinstance(e, str) and e == env_name:
            env_obj = {"name": e, "order": i}
            env_idx = i
            break

    if env_obj is None:
        raise HTTPException(status_code=404, detail=f"Environment '{env_name}' not found")

    # Deploy gating: for env[N], env[N-1] must be deployed (except env[0])
    if env_idx > 0:
        prev_env = envs[env_idx - 1]
        if isinstance(prev_env, dict) and not prev_env.get("deployed"):
            prev_name = prev_env.get("name", f"env[{env_idx-1}]")
            raise HTTPException(status_code=422, detail=f"Cannot deploy {env_name}: {prev_name} must be deployed first")

    # D-13: Block deploy for components with validation errors
    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, env_name)
    if blueprint and blueprint.get("envelope"):
        from packages.core.schemas.base import Envelope
        from packages.core.validation import validate_blueprint

        env_envelope = Envelope.model_validate(blueprint["envelope"])
        issues = validate_blueprint(env_envelope)
        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            blocked_nodes = sorted(set(i.node for i in error_issues if i.node))
            detail = {
                "message": "Deploy blocked due to validation errors",
                "blocked_components": blocked_nodes,
                "errors": [{"node": i.node, "message": i.message} for i in error_issues],
            }
            raise HTTPException(status_code=422, detail=detail)

    # Resolve GCP details from environment entry
    from packages.platform.store.projects import get_env_entry
    env_entry = get_env_entry(envs, env_name) or env_obj

    # Provisioning guard
    provision_status = env_entry.get("provision_status", "")
    if provision_status == "provisioning":
        raise HTTPException(status_code=409, detail=f"Environment '{env_name}' is still provisioning")
    if provision_status == "failed":
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' provisioning failed")
    if provision_status != "ready":
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' is not provisioned")

    gcp_project_id = env_entry.get("gcp_project_id", "")
    tf_bucket = env_entry.get("tf_bucket", "")
    region = env_entry.get("region", "us-central1")

    if not gcp_project_id:
        raise HTTPException(status_code=422, detail=f"Environment '{env_name}' has no GCP project ID")

    deploy_id = deploy_store.create_deploy_record(owner_uid, gcp_project_id, env_name, {
        "project_ref_id": project_ref_id,
        "region": region,
        "tf_bucket": tf_bucket,
    })

    background_tasks.add_task(
        _run_deploy,
        owner_uid, deploy_id, project_ref_id, gcp_project_id,
        env_name, region, tf_bucket,
    )

    return JSONResponse(status_code=202, content={"deploy_id": deploy_id, "status": "pending"})


@router.get("/projects/{project_ref_id}/deploys/{deploy_id}/status")
async def get_deploy_status(deploy_id: str,
                            access: ProjectAccess = Depends(require_project_access("viewer"))):
    status = deploy_store.get_deploy_status(access.owner_uid, deploy_id)
    if not status:
        raise HTTPException(status_code=404, detail="Deploy not found")
    return status


@router.get("/projects/{project_ref_id}/deploys/{deploy_id}/plan")
async def get_deploy_plan(deploy_id: str,
                          access: ProjectAccess = Depends(require_project_access("viewer"))):
    """Return the terraform plan output text for a deploy."""
    import os
    deploy = deploy_store.get_deploy_status(access.owner_uid, deploy_id)
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy not found")

    # Try inline plan_output first
    if deploy.get("plan_output"):
        return {"plan_output": deploy["plan_output"]}

    # Try fetching from GCS via build_id
    build_id = deploy.get("build_id")
    if build_id:
        from packages.platform.gcp.cloud_build import get_build_plan_output
        host_project = os.environ.get("GCP_PROJECT_ID", "pl4m-host")
        plan_text = get_build_plan_output(host_project, build_id)
        if plan_text:
            return {"plan_output": plan_text}

    return {"plan_output": None}


# ── Collaborators ─────────────────────────────────────────────

@router.post("/projects/{project_ref_id}/collaborators")
async def add_collaborator(project_ref_id: str, payload: dict,
                           access: ProjectAccess = Depends(require_project_access("admin"))):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    role = payload.get("role", "editor")
    try:
        result = collab_store.add_collaborator(access.owner_uid, project_ref_id, email, role)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@router.get("/projects/{project_ref_id}/collaborators")
async def list_collaborators(access: ProjectAccess = Depends(require_project_access("viewer"))):
    return collab_store.list_collaborators(access.owner_uid, access.project["id"])


@router.patch("/projects/{project_ref_id}/collaborators/{collaborator_uid}")
async def update_collaborator_role(project_ref_id: str, collaborator_uid: str, payload: dict,
                                   access: ProjectAccess = Depends(require_project_access("admin"))):
    role = payload.get("role")
    if not role:
        raise HTTPException(status_code=422, detail="role is required")
    try:
        result = collab_store.update_collaborator_role(access.owner_uid, project_ref_id, collaborator_uid, role)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return result


@router.delete("/projects/{project_ref_id}/collaborators/{collaborator_uid}")
async def remove_collaborator(project_ref_id: str, collaborator_uid: str,
                              access: ProjectAccess = Depends(require_project_access("admin"))):
    removed = collab_store.remove_collaborator(access.owner_uid, project_ref_id, collaborator_uid)
    if not removed:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return {"removed": True}
