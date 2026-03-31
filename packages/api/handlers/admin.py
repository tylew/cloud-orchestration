"""Admin endpoints — quota management and project reset."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import projects as project_store
from packages.platform.store import tenants as tenant_store
from packages.platform.gcp.secret_manager import list_secrets, delete_secret

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class SetQuotaRequest(BaseModel):
    email: str
    quota: int


class ResetProjectRequest(BaseModel):
    blueprints: bool = True
    deploy_status: bool = True
    secrets: bool = True


@router.put("/quota")
async def set_quota(req: SetQuotaRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tenant = tenant_store.find_tenant_by_email(req.email)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"No tenant found for email {req.email}")
    tenant_store.set_quota(tenant["id"], req.quota)
    return {"ok": True, "tenant_id": tenant["id"], "quota": req.quota}


@router.post("/projects/{project_ref_id}/reset")
async def reset_project(
    project_ref_id: str,
    req: ResetProjectRequest,
    access: ProjectAccess = Depends(require_project_access("admin")),
):
    result = project_store.reset_project_data(
        access.user.tenant_id,
        project_ref_id,
        blueprints=req.blueprints,
        deploy_status=req.deploy_status,
    )

    secrets_deleted = 0
    if req.secrets:
        project_id = access.project.get("project_id", "")
        if project_id:
            try:
                # list_secrets returns [{"name": ..., "secret_id": ..., "create_time": ...}]
                # (verified in packages/platform/gcp/secret_manager.py:50-59)
                secrets = list_secrets(project_id)
                for s in secrets:
                    try:
                        delete_secret(project_id, s["secret_id"])
                        secrets_deleted += 1
                    except Exception as exc:
                        log.warning("Failed to delete secret %s: %s", s["secret_id"], exc)
            except Exception as exc:
                log.warning("Failed to list secrets during project reset: %s", exc)
        else:
            log.warning("No GCP project_id found for project %s; skipping secret cleanup", project_ref_id)

    return {"ok": True, **result, "secrets_deleted": secrets_deleted}


@router.get("/users")
async def list_users(user: CurrentUser = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return tenant_store.list_tenants()
