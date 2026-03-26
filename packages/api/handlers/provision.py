"""Project provisioning endpoint — async with status tracking."""

import logging
import os
import re
import uuid as _uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.store import projects as project_store
from packages.platform.store import tenants as tenant_store
from packages.platform.store import provisioning as provision_store
from packages.platform.gcp.bootstrap import (
    create_gcp_project,
    enable_apis,
    ensure_tenant_folder,
    generate_unique_project_id,
    setup_firebase_auth,
    verify_project_health,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProvisionRequest(BaseModel):
    project_id: str | None = None
    region: str = "us-central1"
    environments: list[str] = []
    display_name: str = ""


@router.post("/provision")
async def provision(req: ProvisionRequest, background_tasks: BackgroundTasks,
                    user: CurrentUser = Depends(get_current_user)):
    # Validate required org config
    missing = []
    for var in ["ORG_ID", "BILLING_ACCOUNT", "TENANTS_FOLDER_ID"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise HTTPException(status_code=500, detail=f"Server misconfigured: missing {', '.join(missing)}")

    display_name = req.display_name or "Untitled"

    # Generate internal project ID: {name-slug}-{uuid8}
    # This is the stable identifier for this project across all envs
    slug = re.sub(r'[^a-z0-9-]', '-', display_name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')[:20]
    internal_id = f"{slug}-{_uuid.uuid4().hex[:8]}" if slug else f"project-{_uuid.uuid4().hex[:8]}"

    # Dev env GCP project ID: dev-{internal_id}
    gcp_project_id = f"dev-{internal_id}"

    # GCP display name must be >= 4 chars
    gcp_display = display_name if len(display_name) >= 4 else f"{display_name}-project"

    # Create single dev env
    environments = [{
        "id": str(_uuid.uuid4()),
        "name": "dev",
        "order": 0,
        "deployed": False,
        "deployed_at": None,
        "gcp_project_id": gcp_project_id,
        "region": req.region,
        "provision_status": "provisioning",
        "provision_id": "",
    }]

    # Quota enforcement
    if not user.is_admin:
        tenant_data = tenant_store.get_tenant(user.tenant_id)
        if tenant_data:
            quota = tenant_data.get("quota", 0)
            used_quota = tenant_data.get("used_quota", 0)
            if used_quota >= quota:
                raise HTTPException(status_code=402, detail="Project quota exceeded")
        else:
            raise HTTPException(status_code=402, detail="Project quota exceeded")

    # Create provision tracking record
    config = {
        "display_name": display_name,
        "region": req.region,
        "internal_project_id": internal_id,
    }
    provision_id = provision_store.create_provision_record(user.tenant_id, gcp_project_id, config)
    environments[0]["provision_id"] = provision_id

    # Create project doc immediately so frontend can navigate to it
    project_result = project_store.save_project(user.tenant_id, {
        "display_name": display_name,
        "internal_project_id": internal_id,
        "region": req.region,
        "environments": environments,
    })
    project_ref_id = project_result["id"]

    # Run provisioning in background (only creates the dev env)
    background_tasks.add_task(
        _run_provisioning,
        user.tenant_id, provision_id, project_ref_id,
        gcp_project_id, gcp_display, internal_id,
        req.region, user.is_admin,
    )

    return JSONResponse(status_code=202, content={
        "provision_id": provision_id,
        "internal_project_id": internal_id,
        "gcp_project_id": gcp_project_id,
        "project_ref_id": project_ref_id,
        "status": "provisioning",
    })


@router.get("/provision/{provision_id}/status")
async def get_provision_status(provision_id: str, user: CurrentUser = Depends(get_current_user)):
    # Provision records are tenant-scoped — only the owner can view their own
    status = provision_store.get_provision_status(user.tenant_id, provision_id)
    if not status:
        raise HTTPException(status_code=404, detail="Provision not found")
    return status


class AddEnvRequest(BaseModel):
    name: str
    region: str = ""


@router.post("/{project_ref_id}/envs")
async def add_environment(project_ref_id: str, req: AddEnvRequest,
                          background_tasks: BackgroundTasks,
                          user: CurrentUser = Depends(get_current_user)):
    """Add a new environment to an existing project, triggering GCP project provisioning."""
    # Validate env name is kebab-case
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", req.name):
        raise HTTPException(status_code=422, detail="Environment name must be kebab-case")

    # Get project
    project = project_store.get_project(user.tenant_id, project_ref_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    envs = project.get("environments", [])

    # Max 3 envs
    if len(envs) >= 3:
        raise HTTPException(status_code=422, detail="Maximum 3 environments allowed")

    # Name unique
    if any(isinstance(e, dict) and e.get("name") == req.name for e in envs):
        raise HTTPException(status_code=409, detail=f"Environment '{req.name}' already exists")

    # Validate org config
    missing = []
    for var in ["ORG_ID", "BILLING_ACCOUNT", "TENANTS_FOLDER_ID"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise HTTPException(status_code=500, detail=f"Server misconfigured: missing {', '.join(missing)}")

    # Resolve region
    region = req.region or next(
        (e.get("region", "us-central1") for e in envs if isinstance(e, dict)),
        "us-central1",
    )

    display_name = project.get("display_name", "project")
    internal_id = project.get("internal_project_id", "")
    if not internal_id:
        raise HTTPException(status_code=422, detail="Project missing internal_project_id")

    # GCP project ID: {env}-{internal_project_id}
    gcp_project_id = f"{req.name}-{internal_id}"
    gcp_display = display_name if len(display_name) >= 4 else f"{display_name}-project"

    # Create env entry
    env_entry = {
        "id": str(_uuid.uuid4()),
        "name": req.name,
        "order": len(envs),
        "deployed": False,
        "deployed_at": None,
        "gcp_project_id": gcp_project_id,
        "region": region,
        "provision_status": "provisioning",
        "provision_id": "",
    }

    # Create provision record
    config = {
        "display_name": display_name,
        "region": region,
        "env_name": req.name,
        "internal_project_id": internal_id,
    }
    provision_id = provision_store.create_provision_record(user.tenant_id, gcp_project_id, config)
    env_entry["provision_id"] = provision_id

    # Add env to project
    envs.append(env_entry)
    project_store.update_project_settings(user.tenant_id, project_ref_id, {"environments": envs})

    # Run provisioning in background
    background_tasks.add_task(
        _run_env_provisioning,
        user.tenant_id, provision_id, project_ref_id, req.name,
        gcp_project_id, gcp_display, internal_id, region, user.is_admin,
    )

    return JSONResponse(status_code=202, content={
        "provision_id": provision_id,
        "env_name": req.name,
        "gcp_project_id": gcp_project_id,
        "status": "provisioning",
    })


def _run_provisioning(tenant_id: str, provision_id: str, project_ref_id: str,
                      gcp_project_id: str, gcp_display_name: str, internal_project_id: str,
                      region: str, is_admin: bool):
    """Background task: provisions the dev GCP project.

    Folder hierarchy: {dev-}tenants/{firebase_uid}/{internal_project_id}/{env}-{internal_project_id}
    """
    tenants_folder_id = os.environ.get("TENANTS_FOLDER_ID", "")
    billing_account = os.environ.get("BILLING_ACCOUNT", "")

    try:
        # Step 1: Ensure tenant folder — dev-tenants/{firebase_uid}
        provision_store.update_provision_status(tenant_id, provision_id, "creating_tenant_folder")
        project_folder_id = None
        if tenants_folder_id:
            try:
                tenant_folder_id = ensure_tenant_folder(tenant_id, tenant_id, tenants_folder_id)
                tenant_store.update_tenant(tenant_id, {"folder_id": tenant_folder_id})
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_tenant_folder",
                    step_result={"step": "ensure_tenant_folder", "success": True, "folder_id": tenant_folder_id},
                )
            except Exception as e:
                log.warning("Failed to create tenant folder: %s", e)
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_tenant_folder",
                    step_result={"step": "ensure_tenant_folder", "success": False, "error": str(e)},
                )
                tenant_folder_id = None

            # Step 2: Create project folder — dev-tenants/{uid}/{internal_project_id}
            if tenant_folder_id:
                try:
                    provision_store.update_provision_status(tenant_id, provision_id, "creating_project_folder")
                    project_folder_id = ensure_tenant_folder(
                        f"{tenant_id}-{internal_project_id}",
                        internal_project_id,
                        tenant_folder_id,
                    )
                    provision_store.update_provision_status(
                        tenant_id, provision_id, "creating_project_folder",
                        step_result={"step": "ensure_project_folder", "success": True, "folder_id": project_folder_id},
                    )
                except Exception as e:
                    log.warning("Failed to create project folder: %s — using tenant folder", e)
                    provision_store.update_provision_status(
                        tenant_id, provision_id, "creating_project_folder",
                        step_result={"step": "ensure_project_folder", "success": False, "error": str(e)},
                    )
                    project_folder_id = tenant_folder_id
        else:
            provision_store.update_provision_status(
                tenant_id, provision_id, "creating_tenant_folder",
                step_result={"step": "ensure_tenant_folder", "skipped": True},
            )

        # Step 3: Create GCP project — dev-{internal_project_id}
        provision_store.update_provision_status(tenant_id, provision_id, "creating_project")
        gcp_result = create_gcp_project(
            gcp_project_id, gcp_display_name,
            billing_account=billing_account or None,
            folder_id=project_folder_id,
        )
        provision_store.update_provision_status(
            tenant_id, provision_id, "creating_project",
            step_result={"step": "create_project", **gcp_result},
        )

        if not gcp_result.get("created") and not gcp_result.get("skipped"):
            _fail_provision(tenant_id, provision_id, project_ref_id,
                           gcp_result.get("error", "Failed to create project"))
            return

        # Step 4: Enable APIs
        provision_store.update_provision_status(tenant_id, provision_id, "enabling_apis")
        api_results = enable_apis(gcp_project_id)
        failed_apis = [a for a in api_results if not a["success"]]
        provision_store.update_provision_status(
            tenant_id, provision_id, "enabling_apis",
            step_result={"step": "enable_apis", "success": len(failed_apis) == 0,
                         "failed": [a["api"] for a in failed_apis]},
        )
        if failed_apis:
            _fail_provision(tenant_id, provision_id, project_ref_id,
                           f"Failed to enable APIs: {', '.join(a['api'] for a in failed_apis)}")
            return

        # Step 5: Setup Firebase Auth
        provision_store.update_provision_status(tenant_id, provision_id, "setup_firebase")
        firebase_result = setup_firebase_auth(gcp_project_id)
        provision_store.update_provision_status(
            tenant_id, provision_id, "setup_firebase",
            step_result={"step": "setup_firebase", "success": firebase_result.get("success", False)},
        )

        # Step 6: Verify health
        provision_store.update_provision_status(tenant_id, provision_id, "verifying")
        health = verify_project_health(gcp_project_id)
        provision_store.update_provision_status(
            tenant_id, provision_id, "verifying",
            step_result={"step": "verify_health", **health},
        )

        # Mark dev env as ready
        _update_env_provision_status(tenant_id, project_ref_id, "dev", "ready")

        if not is_admin:
            tenant_store.increment_used_quota(tenant_id, 1)

        provision_store.update_provision_status(tenant_id, provision_id, "ready")

    except Exception as e:
        log.exception("Provisioning failed for %s", gcp_project_id)
        _fail_provision(tenant_id, provision_id, project_ref_id, str(e))


def _fail_provision(tenant_id, provision_id, project_ref_id, error):
    """Mark provisioning as failed in both provision record and project env."""
    provision_store.update_provision_status(tenant_id, provision_id, "failed", error=error)
    _update_env_provision_status(tenant_id, project_ref_id, "dev", "failed")


def _run_env_provisioning(tenant_id: str, provision_id: str, project_ref_id: str,
                          env_name: str, gcp_project_id: str, gcp_display_name: str,
                          internal_project_id: str, region: str, is_admin: bool):
    """Background task that provisions a GCP project for a new environment.

    GCP project is created inside the existing project folder:
    dev-tenants/{uid}/{internal_project_id}/{env}-{internal_project_id}
    """
    billing_account = os.environ.get("BILLING_ACCOUNT", "")

    try:
        # Get the project folder (created during initial dev provisioning)
        tenant_data = tenant_store.get_tenant(tenant_id)
        tenant_folder_id = tenant_data.get("folder_id") if tenant_data else None
        project_folder_id = None

        if tenant_folder_id:
            try:
                project_folder_id = ensure_tenant_folder(
                    f"{tenant_id}-{internal_project_id}",
                    internal_project_id,
                    tenant_folder_id,
                )
            except Exception as e:
                log.warning("Failed to find/create project folder: %s", e)
                project_folder_id = tenant_folder_id

        # Create GCP project: {env}-{internal_project_id}
        provision_store.update_provision_status(tenant_id, provision_id, "creating_project")
        gcp_result = create_gcp_project(
            gcp_project_id, gcp_display_name,
            billing_account=billing_account or None,
            folder_id=project_folder_id,
        )
        if not gcp_result.get("created") and not gcp_result.get("skipped"):
            _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name,
                                gcp_result.get("error", "Failed to create project"))
            return

        # Enable APIs
        provision_store.update_provision_status(tenant_id, provision_id, "enabling_apis")
        api_results = enable_apis(gcp_project_id)
        failed_apis = [a for a in api_results if not a["success"]]
        if failed_apis:
            _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name,
                                f"Failed to enable APIs: {', '.join(a['api'] for a in failed_apis)}")
            return

        # Setup Firebase Auth
        provision_store.update_provision_status(tenant_id, provision_id, "setup_firebase")
        setup_firebase_auth(gcp_project_id)

        # Verify health
        provision_store.update_provision_status(tenant_id, provision_id, "verifying")
        verify_project_health(gcp_project_id)

        # Update env entry to ready
        _update_env_provision_status(tenant_id, project_ref_id, env_name, "ready")
        provision_store.update_provision_status(tenant_id, provision_id, "ready")

    except Exception as e:
        log.exception("Env provisioning failed for %s/%s", gcp_project_id, env_name)
        _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name, str(e))


def _fail_env_provision(tenant_id, provision_id, project_ref_id, env_name, error):
    """Mark env provisioning as failed in both provision record and project env entry."""
    provision_store.update_provision_status(tenant_id, provision_id, "failed", error=error)
    _update_env_provision_status(tenant_id, project_ref_id, env_name, "failed")


def _update_env_provision_status(tenant_id, project_ref_id, env_name, status):
    """Update provision_status on a specific environment entry in the project doc."""
    project = project_store.get_project(tenant_id, project_ref_id)
    if not project:
        return
    envs = project.get("environments", [])
    for env in envs:
        if isinstance(env, dict) and env.get("name") == env_name:
            env["provision_status"] = status
            break
    project_store.update_project_settings(tenant_id, project_ref_id, {"environments": envs})
