"""Project provisioning endpoint — async with status tracking."""

import logging
import os

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
    create_tf_state_bucket,
    ensure_tenant_folder,
    generate_unique_project_id,
    link_billing,
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

    import uuid as _uuid
    display_name = req.display_name or req.project_id or "Untitled"
    if req.project_id:
        project_id = req.project_id
        tf_bucket = f"{project_id}-tfstate"
    else:
        env_label = os.environ.get("ENVIRONMENT", "dev")
        project_id, tf_bucket = generate_unique_project_id(display_name, environment=env_label)
    # Always create single dev env with UUID
    environments = [{
        "id": str(_uuid.uuid4()),
        "name": "dev",
        "order": 0,
        "deployed": False,
        "deployed_at": None,
        "gcp_project_id": project_id,
        "tf_bucket": tf_bucket,
        "region": req.region,
        "provision_status": "provisioning",
        "provision_id": "",  # set after creating provision record
    }]

    # Quota enforcement — check BEFORE starting background work
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
        "environments": environments,
    }
    provision_id = provision_store.create_provision_record(user.tenant_id, project_id, config)
    environments[0]["provision_id"] = provision_id

    # Run provisioning in background
    background_tasks.add_task(
        _run_provisioning,
        user.tenant_id, provision_id, project_id, display_name,
        req.region, environments, user.is_admin, tf_bucket,
    )

    return JSONResponse(status_code=202, content={
        "provision_id": provision_id,
        "project_id": project_id,
        "tf_bucket": tf_bucket,
        "status": "pending",
    })


@router.get("/provision/{provision_id}/status")
async def get_provision_status(provision_id: str, user: CurrentUser = Depends(get_current_user)):
    # Provision records are tenant-scoped — only the owner can view their own
    status = provision_store.get_provision_status(user.tenant_id, provision_id)
    if not status:
        raise HTTPException(status_code=404, detail="Provision not found")
    return status


def _run_provisioning(tenant_id: str, provision_id: str, project_id: str,
                      display_name: str, region: str, environments: list,
                      is_admin: bool, tf_bucket: str = ""):
    """Background task that runs all provisioning steps."""
    tenants_folder_id = os.environ.get("TENANTS_FOLDER_ID", "")
    billing_account = os.environ.get("BILLING_ACCOUNT", "")

    try:
        # Step 1: Ensure tenant folder exists inside the tenants folder
        provision_store.update_provision_status(tenant_id, provision_id, "creating_tenant_folder")
        if tenants_folder_id:
            try:
                tenant_data = tenant_store.get_tenant(tenant_id)
                tenant_display = tenant_data.get("display_name", tenant_id) if tenant_data else tenant_id
                folder_id = ensure_tenant_folder(tenant_id, tenant_display, tenants_folder_id)
                tenant_store.update_tenant(tenant_id, {"folder_id": folder_id})
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_tenant_folder",
                    step_result={"step": "ensure_tenant_folder", "success": True, "folder_id": folder_id},
                )
            except Exception as e:
                log.warning("Failed to create tenant folder: %s", e)
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_tenant_folder",
                    step_result={"step": "ensure_tenant_folder", "success": False, "error": str(e)},
                )
                folder_id = None
        else:
            folder_id = None
            provision_store.update_provision_status(
                tenant_id, provision_id, "creating_tenant_folder",
                step_result={"step": "ensure_tenant_folder", "skipped": True},
            )

        # Step 1b: Create environment subfolder within tenant folder
        if folder_id:
            env_label = os.environ.get("ENVIRONMENT", "dev")
            try:
                env_folder_id = ensure_tenant_folder(
                    f"{tenant_id}-{env_label}",  # unique ID for env subfolder
                    env_label,                    # display name: "dev" or "prod"
                    folder_id,                    # parent: the tenant folder
                )
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_env_folder",
                    step_result={"step": "ensure_env_folder", "success": True, "folder_id": env_folder_id},
                )
                # Use the env subfolder for project creation instead of the tenant folder
                folder_id = env_folder_id
            except Exception as e:
                log.warning("Failed to create env subfolder: %s — using tenant folder directly", e)
                provision_store.update_provision_status(
                    tenant_id, provision_id, "creating_env_folder",
                    step_result={"step": "ensure_env_folder", "success": False, "error": str(e)},
                )
                # Fall through — folder_id remains the tenant folder

        # Step 2: Create GCP project (inside tenant folder if available)
        provision_store.update_provision_status(tenant_id, provision_id, "creating_project")
        gcp_result = create_gcp_project(
            project_id, display_name,
            billing_account=billing_account or None,
            folder_id=folder_id,
        )
        provision_store.update_provision_status(
            tenant_id, provision_id, "creating_project",
            step_result={"step": "create_project", **gcp_result},
        )

        if not gcp_result.get("created") and not gcp_result.get("skipped"):
            provision_store.update_provision_status(
                tenant_id, provision_id, "failed",
                error=gcp_result.get("error", "Failed to create project"),
            )
            return

        if gcp_result.get("skipped") and not gcp_result.get("exists"):
            log.warning("Project %s doesn't exist and can't be created", project_id)

        # Note: Billing is linked during create_gcp_project() -- no separate step needed.

        # Step 4: Enable APIs
        provision_store.update_provision_status(tenant_id, provision_id, "enabling_apis")
        api_results = enable_apis(project_id)
        failed_apis = [a for a in api_results if not a["success"]]
        provision_store.update_provision_status(
            tenant_id, provision_id, "enabling_apis",
            step_result={"step": "enable_apis", "success": len(failed_apis) == 0,
                         "failed": [a["api"] for a in failed_apis]},
        )
        if failed_apis:
            provision_store.update_provision_status(
                tenant_id, provision_id, "failed",
                error=f"Failed to enable APIs: {', '.join(a['api'] for a in failed_apis)}",
            )
            return

        # Step 5: Create tfstate bucket
        provision_store.update_provision_status(tenant_id, provision_id, "creating_bucket")
        bucket_result = create_tf_state_bucket(project_id, region)
        provision_store.update_provision_status(
            tenant_id, provision_id, "creating_bucket",
            step_result={"step": "create_bucket", **bucket_result},
        )
        if "error" in bucket_result:
            provision_store.update_provision_status(
                tenant_id, provision_id, "failed",
                error=bucket_result["error"],
            )
            return

        # Step 6: Setup Firebase Auth
        provision_store.update_provision_status(tenant_id, provision_id, "setup_firebase")
        firebase_result = setup_firebase_auth(project_id)
        provision_store.update_provision_status(
            tenant_id, provision_id, "setup_firebase",
            step_result={"step": "setup_firebase", "success": firebase_result.get("success", False)},
        )

        # Step 7: Verify health
        provision_store.update_provision_status(tenant_id, provision_id, "verifying")
        health = verify_project_health(project_id)
        provision_store.update_provision_status(
            tenant_id, provision_id, "verifying",
            step_result={"step": "verify_health", **health},
        )

        # Save project reference
        import uuid as _uuid
        final_environments = [{
            "id": str(_uuid.uuid4()),
            "name": "dev",
            "order": 0,
            "deployed": False,
            "deployed_at": None,
            "gcp_project_id": project_id,
            "tf_bucket": tf_bucket,
            "region": region,
            "provision_status": "ready",
            "provision_id": provision_id,
        }]

        project_store.save_project(tenant_id, {
            "display_name": display_name,
            "region": region,
            "environments": final_environments,
        })

        if not is_admin:
            tenant_store.increment_used_quota(tenant_id, 1)

        provision_store.update_provision_status(tenant_id, provision_id, "ready")

    except Exception as e:
        log.exception("Provisioning failed for %s", project_id)
        provision_store.update_provision_status(
            tenant_id, provision_id, "failed",
            error=str(e),
        )
